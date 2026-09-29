"""Deterministic generation engine.

Parents are generated before children (topological FK order). Every column
is generated a whole column at a time with NumPy; text comes from seeded
Faker value pools (`engine/pools.py`). Child FK columns sample parent PKs
that already exist, so FK integrity holds by construction. Rules from the
catalogue are then enforced, and finally the configured null and outlier
rates are applied to columns no rule or key depends on.

The same schema, row counts and seed always give identical output. The AI
is never called here.
"""

import json
from datetime import date, datetime

import numpy as np
import pandas as pd

from app.engine import pools
from app.schemas import ColumnSchema, DatasetSchema, ForeignKey, TableSchema

DEFAULT_ROOT_ROWS = 100

_DEFAULT_START = date(2023, 1, 1)
_DEFAULT_END = date(2025, 12, 31)

_NUMERIC_TYPES = ("integer", "float", "decimal")
_NUMERIC_SEMANTICS = ("quantity", "currency_amount", "percentage", "generic_number")
# default ranges when neither the column nor its profile gives one
_DEFAULT_RANGES = {"quantity": (1.0, 10.0), "percentage": (0.0, 100.0), "currency_amount": (1.0, 1000.0)}

# share of `lte_parent` children that take the full parent value (e.g. a payment in full)
_FULL_PARENT_SHARE = 0.6


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


def generate(
    schema: DatasetSchema,
    rows: dict[str, int],
    seed: int = 42,
    *,
    null_rate: float = 0.0,
    outlier_rate: float = 0.0,
    locale: str = "en_US",
    row_cap: int | None = None,
    notes: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Generate every table. `rows` holds counts for root tables; child counts
    follow the FK cardinality. Child tables above `row_cap` are scaled down
    (a message is appended to `notes`)."""
    if row_cap is None:
        from app.core.config import get_settings

        row_cap = get_settings().row_cap
    notes = notes if notes is not None else []
    rng = np.random.default_rng(seed)
    order = topological_order(schema)
    depth = {t.name: i for i, t in enumerate(order)}
    tables: dict[str, pd.DataFrame] = {}

    for table in order:
        parent_fks = [fk for fk in table.foreign_keys if fk.ref_table in tables and fk.ref_table != table.name]
        # the deepest parent drives the row count (order_items follow orders, not products)
        driver = max(parent_fks, key=lambda fk: depth[fk.ref_table], default=None)

        if driver is None:
            n = rows.get(table.name) or table.row_count_hint or DEFAULT_ROOT_ROWS
            n = max(0, min(int(n), row_cap))
            parent_ids = None
        else:
            parent_pks = tables[driver.ref_table][driver.ref_column].to_numpy()
            counts = _child_counts(driver, len(parent_pks), rng)
            if counts.sum() > row_cap:
                notes.append(
                    f"{table.name} would have {int(counts.sum()):,} rows; capped at {row_cap:,}. "
                    f"Lower the root table rows for full cardinality."
                )
                counts = _cap_counts(counts, driver.min_children, row_cap, rng)
            parent_ids = np.repeat(parent_pks, counts)
            n = len(parent_ids)

        data: dict[str, object] = {}
        for col in table.columns:
            fk = next((f for f in parent_fks if f.column == col.name), None)
            if col.name == table.primary_key:
                data[col.name] = _sequential_ids(table.name, n)
            elif driver is not None and col.name == driver.column:
                data[col.name] = parent_ids
            elif fk is not None:
                pks = tables[fk.ref_table][fk.ref_column].to_numpy()
                data[col.name] = rng.choice(pks, size=n) if len(pks) else np.full(n, None, dtype=object)
            else:
                data[col.name] = _column_values(col, n, rng, locale)
        tables[table.name] = pd.DataFrame(data)

    _apply_rules(schema, tables, rng)
    _apply_noise(schema, tables, rng, null_rate, outlier_rate)
    return tables


# --- cardinality -------------------------------------------------------------


def _child_counts(fk: ForeignKey, n_parents: int, rng: np.random.Generator) -> np.ndarray:
    """Children per parent: from the sampled distribution when there is one,
    otherwise Poisson around the middle of [min_children, max_children]."""
    lo, hi = fk.min_children, max(fk.min_children, fk.max_children)
    if fk.cardinality == "1:1":
        hi = min(hi, 1)
        lo = min(lo, hi)
    dist = fk.children_distribution
    if dist:
        values = np.array([k for k, _ in dist], dtype=np.int64)
        probs = np.array([p for _, p in dist], dtype=float)
        if probs.sum() > 0:
            return np.clip(rng.choice(values, size=n_parents, p=probs / probs.sum()), lo, hi)
    return np.clip(rng.poisson((lo + hi) / 2, size=n_parents), lo, hi)


def _cap_counts(counts: np.ndarray, min_children: int, cap: int, rng: np.random.Generator) -> np.ndarray:
    """Scale counts so they sum to at most `cap`, keeping each parent's
    minimum children for as long as the budget allows."""
    base = np.minimum(counts, min_children)
    if base.sum() >= cap:
        return _truncate(base, cap)
    extra = counts - base
    scaled = np.floor(extra * ((cap - base.sum()) / extra.sum()) + rng.random(len(extra))).astype(np.int64)
    return _truncate(base + scaled, cap)


def _truncate(counts: np.ndarray, cap: int) -> np.ndarray:
    already = np.cumsum(counts) - counts
    return np.minimum(counts, np.maximum(0, cap - already))


# --- column values -----------------------------------------------------------


def _id_prefix(table: str) -> str:
    letters = "".join(ch for ch in table.upper() if ch.isalpha())
    return (letters[:3] or "ID").ljust(3, "X")


def _sequential_ids(name: str, n: int) -> list[str]:
    prefix, width = _id_prefix(name), max(5, len(str(n)))
    return [f"{prefix}-{i:0{width}d}" for i in range(1, n + 1)]


def _column_values(col: ColumnSchema, n: int, rng: np.random.Generator, locale: str) -> np.ndarray | list:
    st, p = col.semantic_type, col.profile
    if col.allowed_values:
        return _categorical(col.allowed_values, p.top_values if p else None, n, rng)
    if col.data_type in ("date", "datetime") or st in ("date", "datetime"):
        return _dates(col, n, rng)
    if col.data_type == "boolean":
        return rng.random(n) < _true_share(p.top_values if p else None)
    if col.data_type in _NUMERIC_TYPES or st in _NUMERIC_SEMANTICS:
        return _numbers(col, n, rng)
    if st in ("category", "status") and p and p.top_values and not col.pii:
        return _categorical([v for v, _ in p.top_values], p.top_values, n, rng)
    if st == "id":
        return np.array(_sequential_ids(col.name, n), dtype=object)
    values = pools.text_values(st, n, rng, locale=locale)
    return _make_unique(values) if col.unique else values


def _categorical(values: list[str], top_values, n: int, rng: np.random.Generator) -> np.ndarray:
    """Pick from `values`, weighted by the sampled frequencies when they exist.
    Values the sample never saw keep a small weight so they still appear."""
    weights = np.ones(len(values))
    if top_values:
        freq = {str(v): f for v, f in top_values}
        seen = np.array([freq.get(str(v), 0.0) for v in values], dtype=float)
        if seen.sum() > 0:
            weights = seen + 0.01 * seen.sum() / len(values)
    return rng.choice(np.array(values, dtype=object), size=n, p=weights / weights.sum())


def _true_share(top_values) -> float:
    for v, f in top_values or []:
        if str(v).lower() in ("true", "1", "yes", "t"):
            return float(f)
    return 0.5


def _as_float(value) -> float | None:
    try:
        return float(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def _num_bounds(col: ColumnSchema) -> tuple[float, float]:
    p = col.profile
    d_lo, d_hi = _DEFAULT_RANGES.get(col.semantic_type, (0.0, 1000.0))
    lo = next((v for v in (_as_float(col.min), _as_float(p.min) if p else None) if v is not None), d_lo)
    hi = next((v for v in (_as_float(col.max), _as_float(p.max) if p else None) if v is not None), None)
    if hi is None:
        hi = max(d_hi, lo * 10 if lo > 0 else d_hi)
    return (hi, lo) if lo > hi else (lo, hi)


def _numbers(col: ColumnSchema, n: int, rng: np.random.Generator) -> np.ndarray:
    lo, hi = _num_bounds(col)
    p = col.profile
    if p and p.histogram and sum(c for _, _, c in p.histogram) > 0:
        bins = np.array(p.histogram, dtype=float)
        pick = rng.choice(len(bins), size=n, p=bins[:, 2] / bins[:, 2].sum())
        values = rng.uniform(bins[pick, 0], bins[pick, 1])
    elif p and p.mean is not None and p.std:
        values = rng.normal(p.mean, p.std, size=n)
    elif col.semantic_type == "currency_amount":
        # right-skewed like real prices: most values low, a long tail up to `hi`
        values = lo + (hi - lo) * rng.beta(1.5, 5.0, size=n)
    else:
        values = rng.uniform(lo, hi, size=n)
    values = np.clip(values, lo, hi)
    if col.data_type == "integer":
        return np.rint(values).astype(np.int64)
    return np.round(values, 2)


def _parse_date(value) -> date | None:
    if value is None or value == "":
        return None
    try:
        return pd.Timestamp(str(value)).date()
    except (ValueError, TypeError):
        return None


def _dates(col: ColumnSchema, n: int, rng: np.random.Generator) -> np.ndarray:
    p = col.profile
    lo = _parse_date(col.min) or (_parse_date(p.min) if p else None) or _DEFAULT_START
    hi = _parse_date(col.max) or (_parse_date(p.max) if p else None) or _DEFAULT_END
    if lo > hi:
        lo, hi = hi, lo
    if col.data_type == "datetime" or col.semantic_type == "datetime":
        start = np.datetime64(datetime(lo.year, lo.month, lo.day), "s")
        span = int((hi - lo).days + 1) * 86_400
        return start + rng.integers(0, span, size=n).astype("timedelta64[s]")
    days = rng.integers(0, (hi - lo).days + 1, size=n)
    return np.datetime64(lo, "D") + days.astype("timedelta64[D]")


def _make_unique(values: np.ndarray) -> np.ndarray:
    s = pd.Series(values, dtype=object)
    dup = s.duplicated()
    if dup.any():
        s[dup] = [f"{v}-{i}" for v, i in zip(s[dup], np.flatnonzero(dup.to_numpy()))]
    return s.to_numpy()


# --- rules -------------------------------------------------------------------


def _apply_rules(schema: DatasetSchema, tables: dict[str, pd.DataFrame], rng: np.random.Generator) -> None:
    """Enforce rules in dependency order: value rules, then dates, then totals, then caps."""
    order = {"range": 0, "allowed_values": 0, "date_order": 1, "sum_of_children": 2, "lte_parent": 3}
    topo = {t.name: i for i, t in enumerate(topological_order(schema))}

    def sort_key(r):
        # dates: parents first, cross-table (via_fk) before same-table.
        # totals: deepest table first so nested sums see their children's totals.
        t = topo.get(r.table, 0)
        return (order[r.kind], -t if r.kind == "sum_of_children" else t, 0 if r.params.get("via_fk") else 1)

    for rule in sorted(schema.rules, key=sort_key):
        df = tables.get(rule.table)
        if df is None or rule.column not in df.columns:
            continue
        p = rule.params
        if rule.kind == "range":
            lo, hi = _as_float(p.get("min")), _as_float(p.get("max"))
            if pd.api.types.is_numeric_dtype(df[rule.column]):
                df[rule.column] = df[rule.column].clip(lower=lo, upper=hi)
        elif rule.kind == "allowed_values":
            allowed = [str(v) for v in p.get("values") or []]
            if allowed:
                bad = ~df[rule.column].astype(str).isin(allowed)
                if bad.any():
                    df.loc[bad, rule.column] = rng.choice(np.array(allowed, dtype=object), size=int(bad.sum()))
        elif rule.kind == "date_order":
            _enforce_date_order(schema, tables, rule.table, rule.column, p, rng)
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
            if fk is None or parent is None or p.get("parent_column") not in parent.columns:
                continue
            cap = df[fk.column].map(parent.set_index(fk.ref_column)[p.get("parent_column")]).astype(float).to_numpy()
            full = rng.random(len(df)) < _FULL_PARENT_SHARE
            partial = np.floor(cap * rng.uniform(0.3, 1.0, size=len(df)) * 100) / 100  # floor: never above the cap
            df[rule.column] = np.where(full, cap, partial)


def _enforce_date_order(schema, tables, table: str, column: str, p: dict, rng: np.random.Generator) -> None:
    """Same-table pairs (issue → due) are regenerated as before + 0..44 days.
    Cross-table pairs (customer created → invoice issued) keep valid dates and
    only move the violating ones."""
    df = tables[table]
    before = _resolve_parent_col(schema, tables, table, p.get("before"), p.get("via_fk"))
    if before is None:
        return
    before = pd.to_datetime(before).to_numpy()
    if p.get("via_fk"):
        after = pd.to_datetime(df[column]).to_numpy()
        bad = after < before
        offset = rng.integers(0, 90, size=int(bad.sum())).astype("timedelta64[D]")
        after = after.copy()
        after[bad] = before[bad] + offset
        df[column] = after
    else:
        offset = rng.integers(0, 45, size=len(df)).astype("timedelta64[D]")
        df[column] = before + offset


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


def _eval_expr(df: pd.DataFrame, expr: str) -> pd.Series | None:
    parts = [p.strip() for p in expr.split("*")]
    if not parts or any(p not in df.columns for p in parts):
        return None
    result = df[parts[0]].astype(float)
    for p in parts[1:]:
        result = result * df[p].astype(float)
    return result


# --- nulls and outliers ------------------------------------------------------


def protected_columns(schema: DatasetSchema) -> set[tuple[str, str]]:
    """(table, column) pairs that keys or rules depend on. Noise never touches them."""
    out: set[tuple[str, str]] = set()
    for t in schema.tables:
        out.add((t.name, t.primary_key))
        out.update((t.name, fk.column) for fk in t.foreign_keys)
        out.update((t.name, c.name) for c in t.columns if c.unique)
    for r in schema.rules:
        p = r.params
        out.add((r.table, r.column))
        for key in ("before", "after", "via_fk"):
            if p.get(key):
                out.add((r.table, str(p[key])))
        if r.kind == "date_order" and p.get("via_fk") and p.get("before"):
            fk = _fk_to_by_column(schema, r.table, str(p["via_fk"]))
            if fk:
                out.add((fk.ref_table, str(p["before"])))
        if r.kind == "sum_of_children" and p.get("child_table"):
            out.update((str(p["child_table"]), part.strip()) for part in str(p.get("expr", "")).split("*"))
        if r.kind == "lte_parent" and p.get("parent_table"):
            out.add((str(p["parent_table"]), str(p.get("parent_column"))))
    return out


def _fk_to_by_column(schema: DatasetSchema, table: str, column: str) -> ForeignKey | None:
    t = schema.table(table)
    return next((fk for fk in t.foreign_keys if fk.column == column), None) if t else None


def _apply_noise(
    schema: DatasetSchema,
    tables: dict[str, pd.DataFrame],
    rng: np.random.Generator,
    null_rate: float,
    outlier_rate: float,
) -> None:
    """Nulls in nullable columns (at least the sampled null rate) and outliers
    in numeric columns, skipping keys and rule columns."""
    protected = protected_columns(schema)
    for t in schema.tables:
        df = tables.get(t.name)
        if df is None or df.empty:
            continue
        for col in t.columns:
            if (t.name, col.name) in protected or col.name not in df.columns:
                continue
            if outlier_rate > 0 and col.data_type in _NUMERIC_TYPES:
                mask = rng.random(len(df)) < outlier_rate
                if mask.any():
                    _, hi = _num_bounds(col)
                    spikes = max(abs(hi), 1.0) * rng.uniform(3.0, 10.0, size=int(mask.sum()))
                    values = df[col.name].to_numpy(dtype=float, copy=True)
                    values[mask] = np.rint(spikes) if col.data_type == "integer" else np.round(spikes, 2)
                    df[col.name] = values.astype(np.int64) if col.data_type == "integer" else values
            rate = max(null_rate, col.profile.null_rate if col.profile else 0.0)
            if col.nullable and rate > 0:
                mask = rng.random(len(df)) < rate
                if mask.any():
                    if col.data_type == "integer":
                        df[col.name] = df[col.name].astype("Int64")
                    elif col.data_type == "boolean":
                        df[col.name] = df[col.name].astype("boolean")
                    df[col.name] = df[col.name].mask(mask)


# --- output ------------------------------------------------------------------


def to_records(df: pd.DataFrame) -> list[dict]:
    """JSON-safe rows: dates as YYYY-MM-DD (datetimes as ISO), NaN/NaT as null,
    numpy scalars as Python."""
    out = df.copy()
    for name in out.columns:
        s = out[name]
        if pd.api.types.is_datetime64_any_dtype(s):
            has_time = bool((s.dropna() != s.dropna().dt.normalize()).any())
            out[name] = s.dt.strftime("%Y-%m-%dT%H:%M:%S" if has_time else "%Y-%m-%d")
    return json.loads(out.to_json(orient="records"))
