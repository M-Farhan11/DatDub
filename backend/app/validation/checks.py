"""Validation report (F6).

Checks per table: table present, PK uniqueness, FK integrity, uniqueness of
other unique columns, types + nullability, and one check per catalogue rule.
The report fails closed: a missing table, column or an unevaluable rule is a
FAIL, never a silent skip.

Injected scenarios (F7) declare exactly which checks they are meant to break
and on which rows (`Expected`: (table, check key) -> row ids). Only those
failures count as `expected_violations`; any other failure on the same row
still fails. Check keys: "pk", "fk:<col>", "unique:<col>", "col:<col>"
(type/nullability of one column), "rule:<rule id>".

Similarity compares the synthetic data with the sample profile (category
TVD, numeric histogram overlap). All checks are vectorized; no AI involved.
"""

import numpy as np
import pandas as pd

from app.ingest.heuristics import BOOL_FALSE, BOOL_TRUE, bool_label
from app.schemas import (
    ColumnSchema,
    DatasetSchema,
    GroundTruthEntry,
    Rule,
    Similarity,
    TableSchema,
    ValidationCheck,
    ValidationReport,
)

_NUMERIC = ("integer", "float", "decimal")
# totals are rounded to cents, so allow a cent of drift
_MONEY_TOL = 0.01

# (table, check key) -> row ids (primary key values) whose failure is intended
Expected = dict[tuple[str, str], set[str]]


def build_report(
    schema: DatasetSchema,
    tables: dict[str, pd.DataFrame],
    ground_truth: list[GroundTruthEntry] | None = None,
    expected: Expected | None = None,
) -> ValidationReport:
    """`expected` excuses specific (check, row) failures; `ground_truth` rows are
    left out of the similarity score."""
    expected = expected or {}
    checks: list[ValidationCheck] = []
    for t in schema.tables:
        df = tables.get(t.name)
        if df is None:
            checks.append(_fail("Table present", t.name, "table is missing from the generated data"))
            continue
        pk = df[t.primary_key].astype(str) if t.primary_key in df.columns else None

        def add(name: str, key: str, ok: pd.Series, unit: str, table: str = t.name, pk=pk) -> None:
            checks.append(_check(name, table, ok, _excused(pk, expected, table, key), unit))

        if pk is None:
            checks.append(_fail("PK uniqueness", t.name, f"primary key column '{t.primary_key}' is missing"))
        else:
            add("PK uniqueness", "pk", ~df[t.primary_key].duplicated(keep=False) & df[t.primary_key].notna(), "unique")
        for fk in t.foreign_keys:
            name = f"FK integrity ({fk.column} → {fk.ref_table})"
            parent = tables.get(fk.ref_table)
            if fk.column not in df.columns or parent is None or fk.ref_column not in parent.columns:
                checks.append(_fail(name, t.name, "foreign key column or parent table/column is missing"))
                continue
            values = df[fk.column]
            # a null FK is a nullability question, not an integrity one
            add(name, f"fk:{fk.column}", values.isna() | values.isin(parent[fk.ref_column]), "resolve")
        for col in t.columns:
            if col.unique and col.name != t.primary_key and col.name in df.columns:
                s = df[col.name]
                add(f"Unique ({col.name})", f"unique:{col.name}", s.isna() | ~s.duplicated(keep=False), "unique")
        checks.append(_types_check(t, df, pk, expected))

    for rule in schema.rules:
        df = tables.get(rule.table)
        t = schema.table(rule.table)
        name = f"Rule {rule.id}: {rule.description or rule.kind}"
        if df is None or t is None:
            checks.append(_fail(name, rule.table, "the rule's table is missing"))
            continue
        ok = _rule_ok(schema, tables, rule)
        if ok is None:
            checks.append(_fail(name, rule.table, "could not evaluate: a referenced table or column is missing"))
            continue
        pk = df[t.primary_key].astype(str) if t.primary_key in df.columns else None
        checks.append(_check(name, rule.table, ok, _excused(pk, expected, rule.table, f"rule:{rule.id}"), "pass"))

    overall = "PASS" if checks and all(c.status == "PASS" for c in checks) else "FAIL"
    return ValidationReport(overall=overall, checks=checks, similarity=similarity(schema, tables, _injected(ground_truth)))


def _injected(ground_truth: list[GroundTruthEntry] | None) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for g in ground_truth or []:
        out.setdefault(g.table, set()).update(str(i) for i in g.affected_ids)
    return out


def _excused(pk: pd.Series | None, expected: Expected, table: str, key: str) -> np.ndarray | None:
    ids = expected.get((table, key))
    if not ids or pk is None:
        return None
    return pk.isin(ids).to_numpy()


def _fail(name: str, table: str, detail: str) -> ValidationCheck:
    return ValidationCheck(name=name, table=table, status="FAIL", score=0.0, detail=detail)


def _check(name: str, table: str, ok: pd.Series, excused: np.ndarray | None, unit: str) -> ValidationCheck:
    """`excused` marks rows whose failure of this check is intended."""
    ok_arr = ok.fillna(False).to_numpy(dtype=bool)
    n_expected = int((~ok_arr & excused).sum()) if excused is not None else 0
    return _summary(name, table, len(ok_arr), int(ok_arr.sum()), n_expected, unit)


def _summary(name: str, table: str, total: int, passed: int, n_expected: int, unit: str) -> ValidationCheck:
    unexpected = total - passed - n_expected
    detail = f"{passed}/{total} {unit}"
    if n_expected:
        detail += f", {n_expected} injected (expected)"
    return ValidationCheck(
        name=name,
        table=table,
        status="PASS" if unexpected == 0 else "FAIL",
        score=round(1.0 if total == 0 else (total - unexpected) / total, 4),
        detail=detail,
        expected_violations=n_expected,
    )


# --- types and nullability ---------------------------------------------------


def _types_check(t: TableSchema, df: pd.DataFrame, pk: pd.Series | None, expected: Expected) -> ValidationCheck:
    """One check per table, attributed per column: a row's failure is expected
    only when every column it fails on was targeted for that row."""
    name = "Types & nullability"
    missing = [c.name for c in t.columns if c.name not in df.columns]
    if missing:
        return _fail(name, t.name, f"missing column(s): {', '.join(missing[:5])}")
    ok_all = np.ones(len(df), dtype=bool)
    unexpected = np.zeros(len(df), dtype=bool)
    for col in t.columns:
        s = df[col.name]
        null = s.isna().to_numpy(dtype=bool)
        ok = null | _type_matches(col, s).fillna(False).to_numpy(dtype=bool)
        if not col.nullable:
            ok &= ~null
        ok_all &= ok
        excused = _excused(pk, expected, t.name, f"col:{col.name}")
        unexpected |= ~ok if excused is None else ~ok & ~excused
    passed = int(ok_all.sum())
    return _summary(name, t.name, len(df), passed, len(df) - passed - int(unexpected.sum()), "rows valid")


def _type_matches(col: ColumnSchema, s: pd.Series) -> pd.Series:
    if col.data_type in _NUMERIC:
        nums = pd.to_numeric(s, errors="coerce").astype(float)
        good = pd.Series(np.isfinite(nums.to_numpy()), index=s.index)  # NaN and ±inf are not values
        if col.data_type == "integer":
            good &= np.isclose(nums.fillna(0) % 1, 0)
        return good
    if col.data_type in ("date", "datetime"):
        if pd.api.types.is_datetime64_any_dtype(s):
            return pd.Series(True, index=s.index)
        return pd.to_datetime(s, errors="coerce", format="mixed").notna()
    if col.data_type == "boolean":
        if pd.api.types.is_bool_dtype(s):
            return pd.Series(True, index=s.index)
        return s.astype(str).str.lower().isin(BOOL_TRUE | BOOL_FALSE)
    return pd.Series(True, index=s.index)


# --- rules -------------------------------------------------------------------


def _rule_ok(schema: DatasetSchema, tables: dict[str, pd.DataFrame], rule: Rule) -> pd.Series | None:
    """Per-row pass mask for `rule` on its table (nulls pass: nullability is a
    separate check). None when the rule cannot be evaluated."""
    df = tables[rule.table]
    p = rule.params
    if rule.column not in df.columns:
        return None
    col = df[rule.column]

    if rule.kind == "range":
        nums = pd.to_numeric(col, errors="coerce")
        lo, hi = _num(p.get("min")), _num(p.get("max"))
        ok = nums.notna()  # a non-numeric value is out of range
        if lo is not None:
            ok &= ~(nums < lo)
        if hi is not None:
            ok &= ~(nums > hi)
        return ok | col.isna()

    if rule.kind == "allowed_values":
        allowed = {str(v) for v in p.get("values") or []}
        if not allowed:
            return None
        return col.isna() | col.astype(str).isin(allowed)

    if rule.kind == "date_order":
        before = _before_series(schema, tables, rule.table, p.get("before"), p.get("via_fk"))
        after_name = p.get("after") or rule.column
        if before is None or after_name not in df.columns:
            return None
        b = pd.to_datetime(before, errors="coerce", format="mixed")
        a = pd.to_datetime(df[after_name], errors="coerce", format="mixed")
        return b.isna() | a.isna() | (b <= a)

    if rule.kind == "sum_of_children":
        child = tables.get(p.get("child_table") or "")
        fk = _fk_to(schema, p.get("child_table"), rule.table)
        t = schema.table(rule.table)
        if child is None or fk is None:
            return None
        line = _eval_expr(child, str(p.get("expr", "")))
        if line is None:
            return None
        sums = line.groupby(child[fk.column]).sum().round(2)
        want = df[t.primary_key].map(sums).fillna(0.0).astype(float)
        got = pd.to_numeric(col, errors="coerce")
        return col.isna() | ((got - want).abs() <= _MONEY_TOL)

    if rule.kind == "lte_parent":
        parent_name, parent_col = p.get("parent_table"), p.get("parent_column")
        parent = tables.get(parent_name or "")
        fk = _fk_to(schema, rule.table, parent_name)
        if parent is None or fk is None or parent_col not in parent.columns:
            return None
        cap = pd.to_numeric(df[fk.column].map(_lookup(parent, fk.ref_column, parent_col)), errors="coerce")
        got = pd.to_numeric(col, errors="coerce")
        return col.isna() | cap.isna() | (got <= cap + 1e-9)

    return None


def _num(value) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _fk_to(schema: DatasetSchema, child_table: str | None, parent_table: str | None):
    t = schema.table(child_table or "")
    return next((fk for fk in t.foreign_keys if fk.ref_table == parent_table), None) if t else None


def _before_series(schema, tables, table: str, col: str | None, via_fk: str | None) -> pd.Series | None:
    df = tables[table]
    if not col:
        return None
    if not via_fk:
        return df[col] if col in df.columns else None
    fk = next((f for f in schema.table(table).foreign_keys if f.column == via_fk), None)
    parent = tables.get(fk.ref_table) if fk else None
    if parent is None or col not in parent.columns or via_fk not in df.columns:
        return None
    return df[via_fk].map(_lookup(parent, fk.ref_column, col))


def _lookup(parent: pd.DataFrame, key: str, col: str) -> pd.Series:
    """key -> col; the first row wins when keys are duplicated (a duplicate PK
    is reported by its own check, it must not break this one)."""
    return parent.drop_duplicates(key).set_index(key)[col]


def _eval_expr(df: pd.DataFrame, expr: str) -> pd.Series | None:
    parts = [p.strip() for p in expr.split("*")]
    if not parts or any(p not in df.columns for p in parts):
        return None
    result = pd.to_numeric(df[parts[0]], errors="coerce")
    for p in parts[1:]:
        result = result * pd.to_numeric(df[p], errors="coerce")
    return result


# --- similarity --------------------------------------------------------------


def similarity(
    schema: DatasetSchema,
    tables: dict[str, pd.DataFrame],
    expected: dict[str, set[str]] | None = None,
) -> Similarity | None:
    """0..1 per profiled column: 1 - TVD for categories, histogram overlap for
    numbers. Keys, unique columns and injected rows are left out. None when no
    column has a sample profile."""
    expected = expected or {}
    per_column: dict[str, float] = {}
    for t in schema.tables:
        df = tables.get(t.name)
        if df is None or df.empty:
            continue
        keys = {t.primary_key, *(fk.column for fk in t.foreign_keys)}
        if expected.get(t.name) and t.primary_key in df.columns:
            df = df[~df[t.primary_key].astype(str).isin(expected[t.name])]
        for col in t.columns:
            prof = col.profile
            if prof is None or col.name in keys or col.unique or col.name not in df.columns:
                continue
            values = df[col.name].dropna()
            if values.empty:
                continue
            score = None
            if prof.histogram and col.data_type in _NUMERIC:
                score = _histogram_overlap(prof.histogram, pd.to_numeric(values, errors="coerce").dropna())
            elif prof.top_values and col.data_type == "boolean":
                labels = values.map(bool_label).dropna()
                top = [(bool_label(v) or str(v), f) for v, f in prof.top_values]
                score = _category_similarity(top, labels) if not labels.empty else None
            elif prof.top_values:
                score = _category_similarity(prof.top_values, values.astype(str))
            if score is not None:
                per_column[f"{t.name}.{col.name}"] = round(score, 4)
    if not per_column:
        return None
    return Similarity(overall=round(float(np.mean(list(per_column.values()))), 4), per_column=per_column)


def _histogram_overlap(histogram, values: pd.Series) -> float | None:
    """Sum of min(profile share, synthetic share) over the profile's bins.
    Synthetic values outside the sampled range lower the score."""
    counts = np.array([c for _, _, c in histogram], dtype=float)
    if counts.sum() <= 0 or values.empty:
        return None
    p = counts / counts.sum()
    v = values.to_numpy(dtype=float)
    q = np.zeros(len(histogram))
    for i, (lo, hi, _) in enumerate(histogram):
        last = i == len(histogram) - 1
        q[i] = np.count_nonzero((v >= lo) & ((v <= hi) if last else (v < hi)))
    q /= len(v)
    return float(np.minimum(p, q).sum())


def _category_similarity(top_values, values: pd.Series) -> float:
    """1 - total variation distance; values outside the profile's top list
    share one 'other' bucket on both sides."""
    p = {str(v): float(f) for v, f in top_values}
    freq = values.value_counts(normalize=True)
    q = {v: float(freq.get(v, 0.0)) for v in p}
    p_other = max(0.0, 1.0 - sum(p.values()))
    q_other = max(0.0, 1.0 - sum(q.values()))
    tvd = 0.5 * (sum(abs(p[v] - q[v]) for v in p) + abs(p_other - q_other))
    return max(0.0, 1.0 - tvd)
