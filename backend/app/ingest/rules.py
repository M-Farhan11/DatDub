"""Infer catalogue rules from complete data (CSV uploads).

A rule is proposed only when it holds for every row that has values, so it
describes the data rather than guessing. Kinds: allowed_values, date_order
(same table), sum_of_children and lte_parent (through an FK).
"""

import itertools

import numpy as np
import pandas as pd

from app.schemas.dataset import DatasetSchema, Rule

_NUMERIC = {"integer", "float", "decimal"}
_TEMPORAL = {"date", "datetime"}
MIN_ROWS = 5


def infer_rules(schema: DatasetSchema, data: dict[str, pd.DataFrame]) -> list[Rule]:
    rules: list[Rule] = []

    def add(kind: str, table: str, column: str, params: dict, description: str) -> None:
        rules.append(Rule(id=f"r{len(rules) + 1}", kind=kind, table=table, column=column, params=params, description=description))

    for t in schema.tables:
        df = data.get(t.name)
        if df is None or len(df) < MIN_ROWS:
            continue
        for c in t.columns:
            if c.allowed_values:
                add("allowed_values", t.name, c.name, {"values": c.allowed_values},
                    f"{t.name}.{c.name} is one of {', '.join(c.allowed_values)}")

        dates = {c.name: _dates(df[c.name]) for c in t.columns if c.data_type in _TEMPORAL and c.name in df}
        for a, b in itertools.permutations(dates, 2):
            both = dates[a].notna() & dates[b].notna()
            if both.sum() >= MIN_ROWS and (dates[a][both] <= dates[b][both]).all() and (dates[a][both] < dates[b][both]).any():
                add("date_order", t.name, b, {"before": a, "after": b}, f"{t.name}.{a} is on or before {b}")

    for child in schema.tables:
        cdf = data.get(child.name)
        for fk in child.foreign_keys:
            parent = schema.table(fk.ref_table)
            pdf = data.get(fk.ref_table)
            if parent is None or cdf is None or pdf is None or len(cdf) < MIN_ROWS:
                continue
            p_num = [c.name for c in parent.columns if c.data_type in _NUMERIC and c.name != parent.primary_key]
            c_num = [c.name for c in child.columns if c.data_type in _NUMERIC and c.name != child.primary_key]
            keys = pdf[parent.primary_key].astype(str)
            fk_vals = cdf[fk.column].astype(str)

            for pcol in p_num:
                for expr in _exprs(c_num):
                    line = _eval(cdf, expr)
                    sums = line.groupby(fk_vals).sum().reindex(keys, fill_value=0.0)
                    target = pd.to_numeric(pdf[pcol], errors="coerce").to_numpy(dtype=float)
                    ok = ~np.isnan(target)
                    has_children = keys.isin(fk_vals).to_numpy()
                    if ok.sum() >= MIN_ROWS and has_children[ok].any() and np.allclose(sums.to_numpy()[ok], target[ok], atol=0.011):
                        add("sum_of_children", parent.name, pcol, {"child_table": child.name, "expr": expr},
                            f"{parent.name}.{pcol} equals the sum of {child.name} {expr}")
                        break

            parent_vals = pdf.set_index(keys)
            for ccol in c_num:
                for pcol in p_num:
                    cap = pd.to_numeric(fk_vals.map(parent_vals[pcol]), errors="coerce")
                    val = pd.to_numeric(cdf[ccol], errors="coerce")
                    both = cap.notna() & val.notna()
                    if both.sum() >= MIN_ROWS and (val[both] <= cap[both] + 1e-9).all() and (val[both] < cap[both]).any() \
                            and _same_kind(child, ccol, parent, pcol):
                        add("lte_parent", child.name, ccol, {"parent_table": parent.name, "parent_column": pcol},
                            f"{child.name}.{ccol} is at most {parent.name}.{pcol}")
    return _dedupe_sums(rules)


def _dates(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", format="mixed")


def _exprs(cols: list[str]) -> list[str]:
    return [*cols, *(f"{a} * {b}" for a, b in itertools.combinations(cols, 2))]


def _eval(df: pd.DataFrame, expr: str) -> pd.Series:
    out = None
    for part in expr.split(" * "):
        s = pd.to_numeric(df[part], errors="coerce").fillna(0.0).astype(float)
        out = s if out is None else out * s
    return out


def _same_kind(child, ccol: str, parent, pcol: str) -> bool:
    """Only compare money with money (avoid 'quantity <= invoice total' coincidences)."""
    sem = lambda t, n: next(c.semantic_type for c in t.columns if c.name == n)  # noqa: E731
    return sem(child, ccol) == sem(parent, pcol) == "currency_amount"


def _dedupe_sums(rules: list[Rule]) -> list[Rule]:
    """A parent column that is the sum of children should not also get an lte rule on the same pair."""
    sums = {(r.params["child_table"], r.table) for r in rules if r.kind == "sum_of_children"}
    kept = [r for r in rules if not (r.kind == "lte_parent" and (r.table, r.params["parent_table"]) in sums)]
    for i, r in enumerate(kept, 1):
        r.id = f"r{i}"
    return kept
