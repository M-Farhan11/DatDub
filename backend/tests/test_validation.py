"""F6: validation report (keys, types, rules, expected violations, similarity)."""

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.engine import generator
from app.main import app
from app.schemas import ColumnProfile, ColumnSchema, DatasetSchema, TableSchema
from app.templates import ecommerce, finance
from app.validation.checks import build_report, similarity
from tests.test_ingest import _upload, finance_csvs

client = TestClient(app)


def _finance(n: int = 300, **kw):
    schema = finance.build()
    return schema, generator.generate(schema, {"customers": n}, seed=5, **kw)


def _check(report, table: str, name_start: str):
    return next(c for c in report.checks if c.table == table and c.name.startswith(name_start))


@pytest.mark.parametrize("build", [finance.build, ecommerce.build])
def test_clean_generation_is_all_pass(build):
    schema = build()
    root = generator.topological_order(schema)[0].name
    tables = generator.generate(schema, {root: 500}, seed=1, null_rate=0.1, outlier_rate=0.05)
    report = build_report(schema, tables)
    assert report.overall == "PASS"
    assert all(c.status == "PASS" and c.score == 1.0 for c in report.checks)
    # every table has key + type checks, every rule has its own check
    for t in schema.tables:
        _check(report, t.name, "PK uniqueness")
        _check(report, t.name, "Types & nullability")
    for r in schema.rules:
        assert any(c.name.startswith(f"Rule {r.id}:") for c in report.checks)


def test_each_broken_row_fails_its_check():
    schema, t = _finance()
    inv, items, pay, cust = t["invoices"], t["invoice_items"], t["payments"], t["customers"]
    cust.loc[1, "customer_id"] = cust.loc[0, "customer_id"]  # duplicate PK (also orphans invoices of row 1)
    items.loc[0, "invoice_id"] = "INV-NOPE"  # orphan FK
    cust.loc[2, "full_name"] = None  # null in a non-nullable column
    items["quantity"] = items["quantity"].astype(object)
    items.loc[1, "quantity"] = "many"  # wrong type, and not in range
    inv.loc[0, "total"] = inv.loc[0, "total"] + 5  # r1 sum_of_children
    inv.loc[1, "due_date"] = inv.loc[1, "issue_date"] - pd.Timedelta(days=3)  # r2 date_order
    pay.loc[0, "amount"] = 10**7  # r3 lte_parent
    inv.loc[2, "status"] = "bogus"  # r6 allowed_values
    items.loc[2, "quantity"] = 99  # r7 range

    report = build_report(schema, t)
    assert report.overall == "FAIL"
    assert _check(report, "customers", "PK uniqueness").detail == f"{len(cust) - 2}/{len(cust)} unique"
    assert _check(report, "invoice_items", "FK integrity").status == "FAIL"
    assert _check(report, "customers", "Types & nullability").status == "FAIL"
    assert _check(report, "invoice_items", "Types & nullability").status == "FAIL"
    for rule_id, table, failed in [("r1", "invoices", 1), ("r2", "invoices", 1), ("r3", "payments", 1), ("r6", "invoices", 1), ("r7", "invoice_items", 2)]:
        c = _check(report, table, f"Rule {rule_id}:")
        n = len(t[table])
        assert c.status == "FAIL" and c.detail == f"{n - failed}/{n} pass", (rule_id, c)
        assert c.score == round((n - failed) / n, 4)
    # untouched checks still pass
    assert _check(report, "payments", "PK uniqueness").status == "PASS"
    assert _check(report, "payments", "Rule r4:").status == "PASS"


def test_cross_table_date_order_fails():
    schema, t = _finance()
    first = t["invoices"].loc[0, "customer_id"]
    t["customers"].loc[t["customers"]["customer_id"] == first, "created_at"] = pd.Timestamp("2099-01-01")
    c = _check(build_report(schema, t), "invoices", "Rule r5:")
    assert c.status == "FAIL" and c.expected_violations == 0


def test_injected_violations_are_expected_not_failures():
    schema, t = _finance()
    pay = t["payments"]
    bad_ids = pay["payment_id"].iloc[:3].tolist()
    pay.loc[pay.index[:3], "amount"] = 10**7
    expected = {("payments", "rule:r3"): set(bad_ids)}

    report = build_report(schema, t, expected=expected)
    c = _check(report, "payments", "Rule r3:")
    assert c.status == "PASS" and c.expected_violations == 3 and c.score == 1.0
    assert "3 injected (expected)" in c.detail
    assert report.overall == "PASS"

    # a violation that is NOT declared still fails
    pay.loc[pay.index[10], "amount"] = 10**7
    c = _check(build_report(schema, t, expected=expected), "payments", "Rule r3:")
    assert c.status == "FAIL" and c.expected_violations == 3


def test_expected_violation_does_not_excuse_other_defects_on_the_same_row():
    """An intended rule break must not hide an unrelated null on that row."""
    schema, t = _finance()
    pay = t["payments"]
    pay.loc[pay.index[0], "amount"] = 10**7
    pay["method"] = pay["method"].astype(object)
    pay.loc[pay.index[0], "method"] = None  # method is required and was not targeted
    expected = {("payments", "rule:r3"): {pay["payment_id"].iloc[0]}}
    report = build_report(schema, t, expected=expected)
    assert _check(report, "payments", "Rule r3:").status == "PASS"
    types = _check(report, "payments", "Types & nullability")
    assert types.status == "FAIL" and types.expected_violations == 0
    assert report.overall == "FAIL"


def test_types_check_is_attributed_per_column():
    schema, t = _finance()
    cust = t["customers"]
    cid = cust["customer_id"].iloc[0]
    cust["full_name"] = cust["full_name"].astype(object)
    cust.loc[cust.index[0], "full_name"] = None
    ok = build_report(schema, t, expected={("customers", "col:full_name"): {cid}})
    assert _check(ok, "customers", "Types & nullability").expected_violations == 1
    assert ok.overall == "PASS"
    # declaring a different column does not excuse it
    wrong = build_report(schema, t, expected={("customers", "col:email"): {cid}})
    assert _check(wrong, "customers", "Types & nullability").status == "FAIL"


def test_report_fails_closed_on_missing_structure():
    schema, t = _finance()
    empty = build_report(schema, {})
    assert empty.overall == "FAIL" and all(c.status == "FAIL" for c in empty.checks)

    t["payments"] = t["payments"].drop(columns=["method"])
    report = build_report(schema, t)
    assert _check(report, "payments", "Types & nullability").status == "FAIL"
    assert report.overall == "FAIL"

    schema2, t2 = _finance()
    t2["invoice_items"] = t2["invoice_items"].drop(columns=["unit_price"])
    c = _check(build_report(schema2, t2), "invoices", "Rule r1:")
    assert c.status == "FAIL" and "could not evaluate" in c.detail


def test_non_finite_numbers_fail_types():
    schema, t = _finance()
    t["invoice_items"]["unit_price"] = t["invoice_items"]["unit_price"].astype(float)
    t["invoice_items"].loc[t["invoice_items"].index[0], "unit_price"] = float("inf")
    assert _check(build_report(schema, t), "invoice_items", "Types & nullability").status == "FAIL"


def test_non_pk_unique_columns_are_checked():
    schema, t = _finance()
    cust = t["customers"]
    cust["email"] = cust["email"].to_numpy(copy=True)
    cust.loc[cust.index[1], "email"] = cust.loc[cust.index[0], "email"]
    c = _check(build_report(schema, t), "customers", "Unique (email)")
    assert c.status == "FAIL" and "298/300" in c.detail


# --- similarity ----------------------------------------------------------------


def _profiled_schema(hist, top) -> DatasetSchema:
    cols = [
        ColumnSchema(name="thing_id", data_type="string", semantic_type="id", unique=True,
                     profile=ColumnProfile(top_values=[("x", 1.0)])),  # keys are never scored
        ColumnSchema(name="score", data_type="float", semantic_type="generic_number", min=0, max=100,
                     profile=ColumnProfile(histogram=hist)),
        ColumnSchema(name="tier", data_type="string", semantic_type="category", allowed_values=["gold", "silver"],
                     profile=ColumnProfile(top_values=top)),
    ]
    return DatasetSchema(name="t", source="csv", tables=[TableSchema(name="things", primary_key="thing_id", columns=cols)])


def test_similarity_high_when_following_profile_low_when_not():
    schema = _profiled_schema([(0, 10, 90), (10, 100, 10)], [("gold", 0.8), ("silver", 0.2)])
    tables = generator.generate(schema, {"things": 5000}, seed=1)
    sim = build_report(schema, tables).similarity
    assert sim is not None and set(sim.per_column) == {"things.score", "things.tier"}
    assert sim.overall > 0.95

    tables["things"]["score"] = 50.0
    tables["things"]["tier"] = "silver"
    sim = similarity(schema, tables)
    assert sim.per_column["things.score"] == 0.1
    assert sim.per_column["things.tier"] == 0.2


def test_similarity_none_without_profiles():
    schema, t = _finance(50)
    assert build_report(schema, t).similarity is None


def test_csv_source_reports_similarity_via_api():
    schema = _upload(finance_csvs()).json()["schema"]
    res = client.post("/api/generate", json={"schema": schema, "rows": {"customers": 200}, "seed": 2})
    report = res.json()["report"]
    assert report["overall"] == "PASS", [c for c in report["checks"] if c["status"] != "PASS"]
    assert report["similarity"] is not None
    assert 0.5 < report["similarity"]["overall"] <= 1.0
    assert any(c["name"].startswith("Rule ") for c in report["checks"])


def test_report_speed_100k():
    import time

    schema = finance.build()
    t = generator.generate(schema, {"customers": 100_000}, seed=1, row_cap=100_000)
    start = time.perf_counter()
    assert build_report(schema, t).overall == "PASS"
    assert time.perf_counter() - start < 5
