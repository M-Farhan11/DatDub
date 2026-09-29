"""Deterministic generation engine.

F0 version: FK-correct, seeded, applies the core rules. F5 extends it with
Faker value pools, profile-based sampling, null/outlier rates and the
row caps.
"""

import json
from datetime import date

import numpy as np
import pandas as pd

from app.schemas import ColumnSchema, DatasetSchema, TableSchema

_FIRST = ["Ava", "Liam", "Noah", "Emma", "Omar", "Sara", "Ali", "Mia", "Zain", "Leah", "Hina", "Ethan"]
_LAST = ["Khan", "Smith", "Ahmed", "Brown", "Garcia", "Malik", "Lee", "Patel", "Chen", "Wilson"]
_CITIES = ["Lahore", "Karachi", "London", "Berlin", "Toronto", "Dubai", "Austin", "Madrid"]
_COUNTRIES = ["Pakistan", "United Kingdom", "Germany", "Canada", "UAE", "United States", "Spain"]
_COMPANIES = ["Acme Ltd", "Globex", "Initech", "Umbrella Co", "Stark Supplies", "Wayne Traders"]
_WORDS = ["Consulting", "License", "Support", "Hardware", "Training", "Hosting", "Design", "Audit"]

_DEFAULT_START = date(2023, 1, 1)
_DEFAULT_END = date(2025, 12, 31)


def topological_order(schema: DatasetSchema) -> list[TableSchema]:
    """Parents before children. Self-references and cycles are ignored."""
    remaining = {t.name: t for t in schema.tables}
    ordered: list[TableSchema] = []
    while remaining:
        ready = [
            t
            for t in remaining.values()
            if all(fk.ref_table not in remaining or fk.ref_table == t.name for fk in t.foreign_keys)
        ]
        if not ready:  # cycle: break it deterministically
            ready = [next(iter(remaining.values()))]
        for t in ready:
            ordered.append(t)
            del remaining[t.name]
    return ordered


def _id_prefix(table: str) -> str:
    letters = "".join(ch for ch in table.upper() if ch.isalpha())
    return (letters[:3] or "ID").ljust(3, "X")


def _date_bounds(col: ColumnSchema) -> tuple[date, date]:
    try:
        lo = date.fromisoformat(str(col.min)) if col.min else _DEFAULT_START
        hi = date.fromisoformat(str(col.max)) if col.max else _DEFAULT_END
    except ValueError:
        lo, hi = _DEFAULT_START, _DEFAULT_END
    return lo, hi


def _column_values(col: ColumnSchema, n: int, rng: np.random.Generator, pk_offset: int = 0) -> np.ndarray | list:
    st = col.semantic_type
    if col.allowed_values:
        return rng.choice(col.allowed_values, size=n)
    if col.data_type in ("date", "datetime") or st in ("date", "datetime"):
        lo, hi = _date_bounds(col)
        days = rng.integers(0, max(1, (hi - lo).days + 1), size=n)
        return (np.datetime64(lo) + days.astype("timedelta64[D]")).astype("datetime64[D]")
    if col.data_type == "boolean":
        return rng.random(n) < 0.5
    if col.data_type in ("integer", "float", "decimal") or st in ("quantity", "currency_amount", "percentage"):
        lo = float(col.min) if col.min is not None else 0.0
        hi = float(col.max) if col.max is not None else (1.0 if st == "percentage" else 1000.0)
        if col.data_type == "integer":
            return rng.integers(int(lo), int(hi) + 1, size=n)
        return np.round(rng.uniform(lo, hi, size=n), 2)
    idx = np.arange(n) + pk_offset
    first = rng.choice(_FIRST, size=n)
    last = rng.choice(_LAST, size=n)
    if st == "person_name":
        return [f"{a} {b}" for a, b in zip(first, last)]
    if st == "first_name":
        return first
    if st == "last_name":
        return last
    if st == "email":
        return [f"{a.lower()}.{b.lower()}{i}@example.com" for a, b, i in zip(first, last, idx)]
    if st == "phone":
        return [f"+1-555-{n_:04d}" for n_ in rng.integers(0, 10_000, size=n)]
    if st == "city":
        return rng.choice(_CITIES, size=n)
    if st == "country":
        return rng.choice(_COUNTRIES, size=n)
    if st == "company":
        return rng.choice(_COMPANIES, size=n)
    if st == "address":
        return [f"{k} {w} Street" for k, w in zip(rng.integers(1, 999, size=n), rng.choice(_LAST, size=n))]
    if st == "sku":
        return [f"SKU-{k:05d}" for k in rng.integers(0, 100_000, size=n)]
    if st == "url":
        return [f"https://example.com/{i}" for i in idx]
    return [f"{w} {i}" for w, i in zip(rng.choice(_WORDS, size=n), idx)]


def generate(schema: DatasetSchema, rows: dict[str, int], seed: int = 42) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    tables: dict[str, pd.DataFrame] = {}

    for table in topological_order(schema):
        parent_fks = [fk for fk in table.foreign_keys if fk.ref_table in tables and fk.ref_table != table.name]
        driver = parent_fks[0] if parent_fks else None

        if driver is None:
            n = rows.get(table.name) or table.row_count_hint or 100
            parent_ids = None
        else:
            parent_pks = tables[driver.ref_table][driver.ref_column].to_numpy()
            hi = driver.max_children if driver.cardinality == "1:N" else min(1, driver.max_children)
            counts = rng.integers(driver.min_children, max(driver.min_children, hi) + 1, size=len(parent_pks))
            parent_ids = np.repeat(parent_pks, counts)
            n = len(parent_ids)

        data: dict[str, object] = {}
        for col in table.columns:
            if col.name == table.primary_key:
                data[col.name] = [f"{_id_prefix(table.name)}-{i:05d}" for i in range(1, n + 1)]
            elif driver is not None and col.name == driver.column:
                data[col.name] = parent_ids
            elif any(fk.column == col.name for fk in parent_fks):
                fk = next(fk for fk in parent_fks if fk.column == col.name)
                data[col.name] = rng.choice(tables[fk.ref_table][fk.ref_column].to_numpy(), size=n)
            else:
                data[col.name] = _column_values(col, n, rng)
        tables[table.name] = pd.DataFrame(data)

    _apply_rules(schema, tables, rng)
    return tables


def _apply_rules(schema: DatasetSchema, tables: dict[str, pd.DataFrame], rng: np.random.Generator) -> None:
    """Enforce rules in dependency order: dates first, then totals, then caps."""
    order = {"range": 0, "allowed_values": 0, "date_order": 1, "sum_of_children": 2, "lte_parent": 3}
    topo = {t.name: i for i, t in enumerate(topological_order(schema))}

    def sort_key(r):
        # date rules: parent tables first, and cross-table (via_fk) before same-table
        return (order[r.kind], topo.get(r.table, 0), 0 if r.params.get("via_fk") else 1)

    for rule in sorted(schema.rules, key=sort_key):
        df = tables.get(rule.table)
        if df is None or rule.column not in df.columns:
            continue
        p = rule.params
        if rule.kind == "date_order":
            before = _resolve_parent_col(schema, tables, rule.table, p.get("before"), p.get("via_fk"))
            if before is None:
                continue
            offset = rng.integers(0, 45, size=len(df)).astype("timedelta64[D]")
            df[rule.column] = (pd.to_datetime(before).to_numpy() + offset).astype("datetime64[D]")
        elif rule.kind == "sum_of_children":
            child_name = p.get("child_table")
            child = tables.get(child_name)
            fk = _fk_to(schema, child_name, rule.table)
            if child is None or fk is None:
                continue
            line = _eval_expr(child, str(p.get("expr", "")))
            if line is None:
                continue
            sums = line.groupby(child[fk.column]).sum()
            parent_pk = schema.table(rule.table).primary_key
            df[rule.column] = df[parent_pk].map(sums).fillna(0).round(2).to_numpy()
        elif rule.kind == "lte_parent":
            fk = _fk_to(schema, rule.table, p.get("parent_table"))
            parent = tables.get(p.get("parent_table"))
            if fk is None or parent is None:
                continue
            cap = df[fk.column].map(parent.set_index(fk.ref_column)[p.get("parent_column")])
            df[rule.column] = (cap * rng.uniform(0.3, 1.0, size=len(df))).round(2).to_numpy()


def _fk_to(schema: DatasetSchema, child_table: str | None, parent_table: str | None):
    t = schema.table(child_table or "")
    return next((fk for fk in t.foreign_keys if fk.ref_table == parent_table), None) if t else None


def _resolve_parent_col(schema, tables, table: str, col: str | None, via_fk: str | None) -> pd.Series | None:
    df = tables[table]
    if not col:
        return None
    if not via_fk:
        return df[col] if col in df.columns else None
    fk = next((f for f in schema.table(table).foreign_keys if f.column == via_fk), None)
    parent = tables.get(fk.ref_table) if fk else None
    if parent is None or col not in parent.columns:
        return None
    return df[via_fk].map(parent.set_index(fk.ref_column)[col])


def to_records(df: pd.DataFrame) -> list[dict]:
    """JSON-safe rows: dates as YYYY-MM-DD, NaN/NaT as null, numpy scalars as Python."""
    out = df.copy()
    for name in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[name]):
            out[name] = out[name].dt.strftime("%Y-%m-%d")
    return json.loads(out.to_json(orient="records"))


def _eval_expr(df: pd.DataFrame, expr: str) -> pd.Series | None:
    parts = [p.strip() for p in expr.split("*")]
    if not parts or any(p not in df.columns for p in parts):
        return None
    result = df[parts[0]].astype(float)
    for p in parts[1:]:
        result = result * df[p].astype(float)
    return result
