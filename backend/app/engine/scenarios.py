"""Scenario injection (F7): deliberate edge cases after clean generation.

Each selected scenario changes a few rows deterministically (seeded) and
records:

- a `GroundTruthEntry` (which rows, what was done, what a system under test
  should do), returned to the user;
- the exact checks it is meant to break (`Expected`: (table, check key) ->
  row ids), including knock-on effects on other tables (a changed line item
  breaks its invoice total). The validator excuses only those failures, so
  an unrelated defect on an injected row still fails the report.

Scenarios touch distinct rows where possible, so their effects do not mix.
The AI never runs here; it only proposed which scenarios to run.
"""

import calendar
from datetime import date

import numpy as np
import pandas as pd

from app.engine.generator import _id_prefix, _num_bounds
from app.schemas import DatasetSchema, GroundTruthEntry, Rule, ScenarioSelection, TableSchema
from app.validation.checks import Expected

_NUMERIC = ("integer", "float", "decimal")
# far past / far future dates that still fit every common database
_FAR_PAST = date(1900, 1, 1)
_FAR_FUTURE = date(2099, 12, 31)


def inject(
    schema: DatasetSchema,
    tables: dict[str, pd.DataFrame],
    selections: list[ScenarioSelection],
    seed: int,
) -> tuple[list[GroundTruthEntry], Expected]:
    """Apply `selections` in order, in place. Returns the ground truth and the expected check failures."""
    rng = np.random.default_rng([seed, 7])  # independent of the generation stream
    expected: Expected = {}
    touched: dict[str, set[str]] = {}
    truth: list[GroundTruthEntry] = []
    for sel in selections:
        p = sel.proposal
        t = schema.table(p.table)
        df = tables.get(p.table)
        if t is None or df is None:
            continue
        injector = _INJECTORS[p.kind]
        ids = injector(schema, tables, t, sel, rng, touched.setdefault(t.name, set()), expected)
        touched[t.name].update(ids)
        truth.append(
            GroundTruthEntry(
                scenario_id=p.id,
                kind=p.kind,
                table=p.table,
                affected_ids=ids,
                description=p.description or p.title,
                expected_behavior=p.expected_behavior,
            )
        )
    return truth, expected


# --- row selection ---------------------------------------------------------------


def _pick(df: pd.DataFrame, t: TableSchema, count: int, rng, touched: set[str], eligible: pd.Series | None = None) -> np.ndarray:
    """Positional indexes of up to `count` rows not used by an earlier scenario."""
    ok = ~df[t.primary_key].astype(str).isin(touched).to_numpy()
    if eligible is not None:
        ok &= eligible.fillna(False).to_numpy(dtype=bool)
    candidates = np.flatnonzero(ok)
    n = min(count, len(candidates))
    return np.sort(rng.choice(candidates, size=n, replace=False)) if n else candidates[:0]


def _ids(df: pd.DataFrame, t: TableSchema, rows: np.ndarray) -> list[str]:
    return df[t.primary_key].iloc[rows].astype(str).tolist()


# --- expected effects -------------------------------------------------------------


def _expect(expected: Expected, table: str, key: str, ids) -> None:
    ids = {str(i) for i in ids}
    if ids:
        expected.setdefault((table, key), set()).update(ids)


def _col_effects(schema: DatasetSchema, tables: dict[str, pd.DataFrame], table: str, column: str, ids: list[str], expected: Expected) -> None:
    """Every check that reads `table.column` on rows `ids`, here and in other tables."""
    t = schema.table(table)
    df = tables[table]
    _expect(expected, table, f"col:{column}", ids)
    rows = df[t.primary_key].astype(str).isin(ids)
    for rule in schema.rules:
        p = rule.params
        key = f"rule:{rule.id}"
        same_table = {rule.column, p.get("after")} | ({p.get("before")} if not p.get("via_fk") else set())
        if rule.table == table and column in same_table:
            _expect(expected, table, key, ids)
        elif rule.kind == "sum_of_children" and p.get("child_table") == table and column in _expr_cols(p):
            fk = _fk_to(schema, table, rule.table)
            if fk:  # the parent's total no longer matches its children
                _expect(expected, rule.table, key, df.loc[rows, fk.column].dropna().astype(str))
        elif rule.kind == "lte_parent" and p.get("parent_table") == table and p.get("parent_column") == column:
            _expect_children(schema, tables, rule, table, ids, expected)
        elif rule.kind == "date_order" and p.get("via_fk") and p.get("before") == column:
            fk = next((f for f in schema.table(rule.table).foreign_keys if f.column == p["via_fk"]), None)
            if fk and fk.ref_table == table:
                _expect_children(schema, tables, rule, table, ids, expected)


def _expect_children(schema, tables, rule: Rule, parent: str, parent_ids: list[str], expected: Expected) -> None:
    child_t = schema.table(rule.table)
    fk = next((f for f in child_t.foreign_keys if f.ref_table == parent), None)
    child = tables.get(rule.table)
    if fk is None or child is None:
        return
    hit = child[fk.column].astype(str).isin(parent_ids)
    _expect(expected, rule.table, f"rule:{rule.id}", child.loc[hit, child_t.primary_key].astype(str))


def _expr_cols(p: dict) -> set[str]:
    return {x.strip() for x in str(p.get("expr") or "").split("*")}


def _fk_to(schema: DatasetSchema, child: str, parent: str):
    t = schema.table(child)
    return next((fk for fk in t.foreign_keys if fk.ref_table == parent), None) if t else None


# --- injectors --------------------------------------------------------------------


def _null_burst(schema, tables, t, sel, rng, touched, expected) -> list[str]:
    df, col = tables[t.name], sel.proposal.column
    rows = _pick(df, t, sel.count, rng, touched, df[col].notna())
    _set(df, col, rows, None)
    ids = _ids(df, t, rows)
    _col_effects(schema, tables, t.name, col, ids, expected)
    return ids


def _extreme_value(schema, tables, t, sel, rng, touched, expected) -> list[str]:
    df, col = tables[t.name], sel.proposal.column
    cs = next(c for c in t.columns if c.name == col)
    rows = _pick(df, t, sel.count, rng, touched)
    observed = pd.to_numeric(df[col], errors="coerce").abs().max()
    base = max(abs(_num_bounds(cs)[1]), float(observed) if pd.notna(observed) else 0.0, 1.0)
    values = base * rng.uniform(20.0, 100.0, size=len(rows))  # 20-100x the largest normal value
    values = np.rint(values) if cs.data_type == "integer" else np.round(values, 2)
    _set(df, col, rows, values)
    ids = _ids(df, t, rows)
    _col_effects(schema, tables, t.name, col, ids, expected)
    return ids


def _boundary_date(schema, tables, t, sel, rng, touched, expected) -> list[str]:
    df, col = tables[t.name], sel.proposal.column
    rows = _pick(df, t, sel.count, rng, touched)
    current = pd.to_datetime(df[col], errors="coerce").dropna()
    year = int(current.dt.year.median()) if not current.empty else 2024
    leap = next(y for y in range(year, year + 4) if calendar.isleap(y))
    month = int(rng.integers(1, 13))
    boundaries = [
        date(year, month, calendar.monthrange(year, month)[1]),  # month end
        date(leap, 2, 29),  # leap day
        date(year, 12, 31),  # year end
        date(year, 1, 1),  # year start
        _FAR_PAST,
        _FAR_FUTURE,
    ]
    order = rng.permutation(len(rows))
    _set(df, col, rows, pd.to_datetime([boundaries[i % len(boundaries)] for i in order]).to_numpy())
    ids = _ids(df, t, rows)
    _col_effects(schema, tables, t.name, col, ids, expected)
    return ids


def _duplicate_record(schema, tables, t, sel, rng, touched, expected) -> list[str]:
    """Copies of existing rows under new primary keys (e.g. a payment booked twice)."""
    df = tables[t.name]
    rows = _pick(df, t, sel.count, rng, touched)
    if not len(rows):
        return []
    copies = df.iloc[rows].copy()
    new_ids = _next_ids(df[t.primary_key].astype(str), t.name, len(rows))
    source_ids = copies[t.primary_key].astype(str).tolist()
    copies[t.primary_key] = new_ids
    tables[t.name] = pd.concat([df, copies], ignore_index=True)

    for c in t.columns:  # copied unique values now appear twice (both rows fail uniqueness)
        if c.unique and c.name != t.primary_key:
            _expect(expected, t.name, f"unique:{c.name}", new_ids + source_ids)
    for rule in schema.rules:
        p = rule.params
        if rule.kind == "sum_of_children" and rule.table == t.name:  # a copied header has no children of its own
            _expect(expected, t.name, f"rule:{rule.id}", new_ids)
        elif rule.kind == "sum_of_children" and p.get("child_table") == t.name:  # a copied line item inflates its parent
            fk = _fk_to(schema, t.name, rule.table)
            if fk:
                _expect(expected, rule.table, f"rule:{rule.id}", copies[fk.column].dropna().astype(str))
    touched.update(source_ids)
    return new_ids


def _rule_violation(schema, tables, t, sel, rng, touched, expected) -> list[str]:
    rule = next(r for r in schema.rules if r.id == sel.proposal.rule_id)
    df = tables[t.name]
    p = rule.params
    col = rule.column
    cs = next(c for c in t.columns if c.name == col)

    if rule.kind == "range":
        rows = _pick(df, t, sel.count, rng, touched)
        lo, hi = _num(p.get("min")), _num(p.get("max"))
        if hi is not None:
            values = hi + np.maximum(abs(hi) * rng.uniform(0.1, 1.0, size=len(rows)), 1.0)
        else:
            values = lo - np.maximum(abs(lo) * rng.uniform(0.1, 1.0, size=len(rows)), 1.0)
        if cs.data_type == "integer":
            values = np.ceil(values) if hi is not None else np.floor(values)
        else:
            values = np.round(values, 2)
    elif rule.kind == "allowed_values":
        rows = _pick(df, t, sel.count, rng, touched)
        allowed = {str(v) for v in p.get("values") or []}
        bad = next(v for v in ("UNKNOWN", "unknown_value", "INVALID", "__invalid__") if v not in allowed)
        values = np.full(len(rows), bad, dtype=object)
    elif rule.kind == "date_order":
        before = _before(schema, tables, t, p)
        rows = _pick(df, t, sel.count, rng, touched, before.notna())
        days = rng.integers(1, 31, size=len(rows)).astype("timedelta64[D]")
        values = pd.to_datetime(before.iloc[rows]).to_numpy() - days  # 1-30 days too early
    elif rule.kind == "sum_of_children":
        rows = _pick(df, t, sel.count, rng, touched)
        current = pd.to_numeric(df[col].iloc[rows], errors="coerce").fillna(0.0).to_numpy(dtype=float)
        values = np.round(current + np.maximum(np.abs(current) * rng.uniform(0.05, 0.25, size=len(rows)), 1.0), 2)
    elif rule.kind == "lte_parent":
        fk = _fk_to(schema, t.name, p.get("parent_table"))
        parent = tables[p["parent_table"]]
        cap = pd.to_numeric(df[fk.column].map(parent.drop_duplicates(fk.ref_column).set_index(fk.ref_column)[p["parent_column"]]), errors="coerce")
        rows = _pick(df, t, sel.count, rng, touched, cap.notna())
        caps = cap.iloc[rows].to_numpy(dtype=float)
        values = np.round(caps + np.maximum(np.abs(caps) * rng.uniform(0.1, 0.5, size=len(rows)), 1.0), 2)
        if cs.data_type == "integer":
            values = np.ceil(values)
    else:
        return []

    _set(df, col, rows, values)
    ids = _ids(df, t, rows)
    _col_effects(schema, tables, t.name, col, ids, expected)
    _expect(expected, t.name, f"rule:{rule.id}", ids)
    return ids


_INJECTORS = {
    "null_burst": _null_burst,
    "extreme_value": _extreme_value,
    "boundary_date": _boundary_date,
    "duplicate_record": _duplicate_record,
    "rule_violation": _rule_violation,
}


# --- helpers ------------------------------------------------------------------------


def _set(df: pd.DataFrame, col: str, rows: np.ndarray, values) -> None:
    """Write `values` into positional `rows` of `col`, widening the dtype when needed."""
    if not len(rows):
        return
    s = df[col]
    if values is None:
        if pd.api.types.is_integer_dtype(s) and not isinstance(s.dtype, pd.Int64Dtype):
            s = s.astype("Int64")
        elif pd.api.types.is_bool_dtype(s):
            s = s.astype("boolean")
        s = s.copy()
        s.iloc[rows] = None
    else:
        if pd.api.types.is_integer_dtype(s) and not isinstance(values[0], str):
            whole = np.all(np.mod(np.asarray(values, dtype=float), 1) == 0)
            s = s.astype(s.dtype if whole else float)
            values = np.asarray(values, dtype=np.int64 if whole else float)
        s = s.copy()
        s.iloc[rows] = values
    df[col] = s


def _next_ids(existing: pd.Series, table: str, n: int) -> list[str]:
    prefix = _id_prefix(table)
    nums = pd.to_numeric(existing.str.extract(rf"^{prefix}-(\d+)$")[0], errors="coerce")
    start = int(nums.max()) + 1 if nums.notna().any() else len(existing) + 1
    width = max(5, len(str(start + n)))
    taken = set(existing)
    out, i = [], start
    while len(out) < n:
        candidate = f"{prefix}-{i:0{width}d}"
        if candidate not in taken:
            out.append(candidate)
        i += 1
    return out


def _before(schema: DatasetSchema, tables, t: TableSchema, p: dict) -> pd.Series:
    df = tables[t.name]
    if not p.get("via_fk"):
        return df[p["before"]]
    fk = next(f for f in t.foreign_keys if f.column == p["via_fk"])
    parent = tables[fk.ref_table]
    return df[fk.column].map(parent.drop_duplicates(fk.ref_column).set_index(fk.ref_column)[p["before"]])


def _num(value) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None
