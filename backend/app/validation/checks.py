"""Validation report (F6).

Checks per table: PK uniqueness, FK integrity, types + nullability, and one
check per catalogue rule. Rows listed in the ground truth (injected
scenarios, F7) that fail a check on their own table count as
`expected_violations`, not failures. Similarity compares the synthetic data
with the sample profile (category TVD, numeric histogram overlap).

All checks are vectorized; no AI involved.
"""

import numpy as np
import pandas as pd

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
_BOOL_VALUES = {"true", "false", "1", "0", "1.0", "0.0"}
# totals are rounded to cents, so allow a cent of drift
_MONEY_TOL = 0.01


def build_report(
    schema: DatasetSchema,
    tables: dict[str, pd.DataFrame],
    ground_truth: list[GroundTruthEntry] | None = None,
) -> ValidationReport:
    expected = _expected_ids(ground_truth or [])
    checks: list[ValidationCheck] = []
    for t in schema.tables:
        df = tables.get(t.name)
        if df is None:
            continue
        pk = df[t.primary_key] if t.primary_key in df.columns else None
        exp = expected.get(t.name, set())

        def add(name: str, ok: pd.Series, unit: str, table: str = t.name) -> None:
            checks.append(_check(name, table, ok, pk, exp, unit))

        if pk is not None:
            add("PK uniqueness", ~pk.duplicated(keep=False) & pk.notna(), "unique")
        for fk in t.foreign_keys:
            parent = tables.get(fk.ref_table)
            if parent is None or fk.column not in df.columns or fk.ref_column not in parent.columns:
                continue
            values = df[fk.column]
            # a null FK is a nullability question, not an integrity one
            add(f"FK integrity ({fk.column} → {fk.ref_table})", values.isna() | values.isin(parent[fk.ref_column]), "resolve")
        add("Types & nullability", _types_ok(t, df), "rows valid")

    for rule in schema.rules:
        df = tables.get(rule.table)
        t = schema.table(rule.table)
        if df is None or t is None:
            continue
        ok = _rule_ok(schema, tables, rule)
        if ok is None:
            continue
        pk = df[t.primary_key] if t.primary_key in df.columns else None
        checks.append(_check(f"Rule {rule.id}: {rule.description or rule.kind}", rule.table, ok, pk, expected.get(rule.table, set()), "pass"))

    overall = "PASS" if all(c.status == "PASS" for c in checks) else "FAIL"
    return ValidationReport(overall=overall, checks=checks, similarity=similarity(schema, tables, expected))


def _expected_ids(ground_truth: list[GroundTruthEntry]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for g in ground_truth:
        out.setdefault(g.table, set()).update(str(i) for i in g.affected_ids)
    return out


def _check(name: str, table: str, ok: pd.Series, pk: pd.Series | None, expected: set[str], unit: str) -> ValidationCheck:
    ok = ok.fillna(False).astype(bool)
    total = len(ok)
    failed = ~ok
    n_expected = 0
    if expected and pk is not None and failed.any():
        n_expected = int((failed & pk.astype(str).isin(expected)).sum())
    passed = int(ok.sum())
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


def _types_ok(t: TableSchema, df: pd.DataFrame) -> pd.Series:
    ok = pd.Series(True, index=df.index)
    for col in t.columns:
        if col.name not in df.columns:
            continue
        s = df[col.name]
        null = s.isna()
        if not col.nullable:
            ok &= ~null
        ok &= null | _type_matches(col, s)
    return ok


def _type_matches(col: ColumnSchema, s: pd.Series) -> pd.Series:
    if col.data_type in _NUMERIC:
        nums = pd.to_numeric(s, errors="coerce")
        good = nums.notna()
        if col.data_type == "integer":
            good &= np.isclose(nums.fillna(0).astype(float) % 1, 0)
        return good
    if col.data_type in ("date", "datetime"):
        if pd.api.types.is_datetime64_any_dtype(s):
            return pd.Series(True, index=s.index)
        return pd.to_datetime(s, errors="coerce", format="mixed").notna()
    if col.data_type == "boolean":
        if pd.api.types.is_bool_dtype(s):
            return pd.Series(True, index=s.index)
        return s.astype(str).str.lower().isin(_BOOL_VALUES)
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
