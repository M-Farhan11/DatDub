"""Validation report.

F0 version: PK uniqueness and FK integrity. F6 adds type/nullability,
per-rule checks, expected (injected) violations and similarity.
"""

import pandas as pd

from app.schemas import DatasetSchema, ValidationCheck, ValidationReport


def _check(name: str, table: str, ok: int, total: int, unit: str) -> ValidationCheck:
    score = 1.0 if total == 0 else ok / total
    return ValidationCheck(
        name=name,
        table=table,
        status="PASS" if ok == total else "FAIL",
        score=round(score, 4),
        detail=f"{ok}/{total} {unit}",
    )


def build_report(schema: DatasetSchema, tables: dict[str, pd.DataFrame]) -> ValidationReport:
    checks: list[ValidationCheck] = []
    for t in schema.tables:
        df = tables.get(t.name)
        if df is None:
            continue
        if t.primary_key in df.columns:
            pk = df[t.primary_key]
            ok = int((~pk.duplicated(keep=False) & pk.notna()).sum())
            checks.append(_check("PK uniqueness", t.name, ok, len(df), "unique"))
        for fk in t.foreign_keys:
            parent = tables.get(fk.ref_table)
            if parent is None or fk.column not in df.columns:
                continue
            values = df[fk.column].dropna()
            ok = int(values.isin(parent[fk.ref_column]).sum())
            checks.append(_check(f"FK integrity ({fk.column} → {fk.ref_table})", t.name, ok, len(values), "resolve"))
    overall = "PASS" if all(c.status == "PASS" for c in checks) else "FAIL"
    return ValidationReport(overall=overall, checks=checks, similarity=None)
