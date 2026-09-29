"""F5: generation engine (determinism, integrity, rules, cardinality, caps, noise, speed)."""

import time

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.engine import generator, store
from app.main import app
from app.schemas import ColumnProfile, ColumnSchema, DatasetSchema, ForeignKey, Rule, TableSchema
from app.templates import ecommerce, finance

client = TestClient(app)


def _fk_ok(tables, schema) -> bool:
    for t in schema.tables:
        for fk in t.foreign_keys:
            if not tables[t.name][fk.column].isin(tables[fk.ref_table][fk.ref_column]).all():
                return False
    return True


@pytest.mark.parametrize("build", [finance.build, ecommerce.build])
def test_templates_generate_with_integrity(build):
    schema = build()
    root = generator.topological_order(schema)[0].name
    tables = generator.generate(schema, {root: 500}, seed=1)
    assert len(tables[root]) == 500
    for t in schema.tables:
        assert tables[t.name][t.primary_key].is_unique
    assert _fk_ok(tables, schema)


def test_same_seed_same_output_different_seed_differs():
    schema = finance.build()
    a = generator.generate(schema, {"customers": 300}, seed=7)
    b = generator.generate(schema, {"customers": 300}, seed=7)
    c = generator.generate(schema, {"customers": 300}, seed=8)
    for name in a:
        pd.testing.assert_frame_equal(a[name], b[name])
    assert not a["customers"].equals(c["customers"])


def test_finance_rules_hold():
    schema = finance.build()
    t = generator.generate(schema, {"customers": 1000}, seed=3)
    inv, items, pay, cust = t["invoices"], t["invoice_items"], t["payments"], t["customers"]

    line = (items["quantity"] * items["unit_price"]).groupby(items["invoice_id"]).sum()
    totals = inv.set_index("invoice_id")["total"]
    assert np.allclose(totals.loc[line.index], line.round(2), atol=0.01)

    assert (inv["due_date"] >= inv["issue_date"]).all()
    created = inv["customer_id"].map(cust.set_index("customer_id")["created_at"])
    assert (inv["issue_date"] >= created).all()

    inv_total = pay["invoice_id"].map(totals)
    assert (pay["amount"] <= inv_total + 1e-9).all()
    issue = pay["invoice_id"].map(inv.set_index("invoice_id")["issue_date"])
    assert (pay["paid_at"] >= issue).all()

    assert inv["status"].isin(finance.INVOICE_STATUSES).all()
    assert items["quantity"].between(1, 20).all()
    # every invoice has 1..6 items
    per_inv = items.groupby("invoice_id").size()
    assert per_inv.min() >= 1 and per_inv.max() <= 6


def test_text_columns_use_pools_and_emails_unique():
    t = generator.generate(finance.build(), {"customers": 2000}, seed=5)
    cust = t["customers"]
    assert cust["email"].is_unique
    assert cust["full_name"].str.contains(" ").all()
    assert cust["full_name"].nunique() > 500  # pools, not a dozen hard-coded names


def _one_table(col: ColumnSchema) -> DatasetSchema:
    return DatasetSchema(
        name="t",
        source="csv",
        tables=[TableSchema(name="things", primary_key="id", columns=[ColumnSchema(name="id", data_type="string", semantic_type="id"), col])],
    )


def test_profile_histogram_and_categories_are_followed():
    hist_col = ColumnSchema(
        name="score",
        data_type="float",
        semantic_type="generic_number",
        min=0,
        max=100,
        profile=ColumnProfile(histogram=[(0, 10, 90), (10, 100, 10)]),
    )
    df = generator.generate(_one_table(hist_col), {"things": 20_000}, seed=2)["things"]
    assert 0.85 < (df["score"] < 10).mean() < 0.95

    cat_col = ColumnSchema(
        name="tier",
        data_type="string",
        semantic_type="category",
        allowed_values=["gold", "silver"],
        profile=ColumnProfile(top_values=[("gold", 0.8), ("silver", 0.2)]),
    )
    df = generator.generate(_one_table(cat_col), {"things": 20_000}, seed=2)["things"]
    assert 0.75 < (df["tier"] == "gold").mean() < 0.85


def test_children_distribution_is_followed():
    schema = DatasetSchema(
        name="t",
        source="csv",
        tables=[
            TableSchema(name="parents", primary_key="pid", columns=[ColumnSchema(name="pid", data_type="string", semantic_type="id")]),
            TableSchema(
                name="kids",
                primary_key="kid",
                columns=[
                    ColumnSchema(name="kid", data_type="string", semantic_type="id"),
                    ColumnSchema(name="pid", data_type="string", semantic_type="id"),
                ],
                foreign_keys=[
                    ForeignKey(column="pid", ref_table="parents", ref_column="pid", min_children=0, max_children=3,
                               children_distribution=[(0, 0.5), (3, 0.5)])
                ],
            ),
        ],
    )
    t = generator.generate(schema, {"parents": 4000}, seed=4)
    per_parent = t["kids"]["pid"].value_counts()
    assert set(per_parent.unique()) == {3}
    assert 0.45 < len(per_parent) / 4000 < 0.55


def test_child_tables_are_capped_but_keep_min_children():
    notes: list[str] = []
    t = generator.generate(finance.build(), {"customers": 2000}, seed=1, row_cap=3000, notes=notes)
    assert all(len(df) <= 3000 for df in t.values())
    assert notes and "capped" in notes[0]
    # invoices were capped, items keep at least one per invoice while the budget allows
    assert _fk_ok(t, finance.build())
    assert t["invoices"]["invoice_id"].isin(t["invoice_items"]["invoice_id"]).all()


def test_null_and_outlier_rates_skip_keys_and_rule_columns():
    schema = finance.build()
    t = generator.generate(schema, {"customers": 5000}, seed=9, null_rate=0.2, outlier_rate=0.1)
    cust = t["customers"]
    assert 0.15 < cust["phone"].isna().mean() < 0.25  # nullable
    assert cust["email"].notna().all()  # not nullable
    for tbl in schema.tables:
        assert t[tbl.name][tbl.primary_key].notna().all()
    items = t["invoice_items"]
    assert items["quantity"].between(1, 20).all()  # rule columns keep their range


def test_outliers_on_free_numeric_column():
    col = ColumnSchema(name="weight", data_type="float", semantic_type="generic_number", min=0, max=10)
    df = generator.generate(_one_table(col), {"things": 10_000}, seed=1, outlier_rate=0.05)["things"]
    assert 0.03 < (df["weight"] > 10).mean() < 0.07


def test_to_records_formats_dates_and_nulls():
    t = generator.generate(finance.build(), {"customers": 50}, seed=1, null_rate=0.5)
    rec = generator.to_records(t["customers"])
    assert len(rec[0]["created_at"]) == 10
    assert any(r["phone"] is None for r in rec)


def test_speed_5k_customers_under_5s():
    generator.generate(finance.build(), {"customers": 10}, seed=0)  # warm the pools
    start = time.perf_counter()
    generator.generate(finance.build(), {"customers": 5000}, seed=1)
    assert time.perf_counter() - start < 5


def test_speed_100k_customers_under_30s():
    start = time.perf_counter()
    t = generator.generate(finance.build(), {"customers": 100_000}, seed=1, row_cap=100_000)
    assert time.perf_counter() - start < 30
    assert len(t["customers"]) == 100_000


def test_api_generate_and_page_and_limit():
    store.clear()
    schema = client.get("/api/templates/finance").json()
    res = client.post("/api/generate", json={"schema": schema, "rows": {"customers": 200}, "seed": 1, "null_rate": 0.1})
    assert res.status_code == 200
    body = res.json()
    assert body["row_counts"]["customers"] == 200
    assert all(len(rows) <= 50 for rows in body["previews"].values())

    page = client.get(f"/api/datasets/{body['dataset_id']}/tables/invoices", params={"offset": 10, "limit": 5}).json()
    assert page["total"] == body["row_counts"]["invoices"] and len(page["rows"]) == 5

    too_big = client.post("/api/generate", json={"schema": schema, "rows": {"customers": 10_000_000}})
    assert too_big.status_code == 422 and too_big.json()["error"]["code"] == "rows_limit_exceeded"


def test_range_rule_bounds_drive_generation_not_just_clipping():
    # AI drafts often give the range only as a rule (GPA 0-4), not on the column
    schema = DatasetSchema(
        name="uni",
        source="prompt",
        tables=[
            TableSchema(
                name="student",
                primary_key="student_id",
                columns=[
                    ColumnSchema(name="student_id", data_type="string", semantic_type="id"),
                    ColumnSchema(name="gpa", data_type="float", semantic_type="generic_number"),
                    ColumnSchema(name="credits", data_type="integer", semantic_type="quantity"),
                ],
            )
        ],
        rules=[
            Rule(id="r1", kind="range", table="student", column="gpa", params={"min": 0, "max": 4}),
            Rule(id="r2", kind="range", table="student", column="credits", params={"min": 1, "max": 4}),
        ],
    )
    df = generator.generate(schema, {"student": 1000}, seed=3)["student"]
    assert df["gpa"].between(0, 4).all() and df["gpa"].nunique() > 100
    assert (df["gpa"] == 4).mean() < 0.05
    assert set(df["credits"]) == {1, 2, 3, 4}
