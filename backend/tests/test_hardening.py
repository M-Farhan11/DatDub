"""Regression tests for the pre-F7 review (request admission, uniqueness,
rule order, precision, booleans, categories, privacy, limits)."""

import io

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.ai.schemas import DraftColumn, DraftForeignKey, DraftRule, DraftScenario, DraftTable, ScenarioPlan, SchemaDraft
from app.ai.validate import draft_to_schema, validate_proposals
from app.core.exceptions import InvalidSchema
from app.engine import generator, store
from app.engine.store import GeneratedDataset
from app.ingest.build import column_from_values
from app.ingest.enrich import build_ai_payload
from app.ingest.profiler import profile_column
from app.main import app
from app.schemas import ColumnSchema, DatasetSchema, Rule, TableSchema, ValidationReport
from app.templates import finance
from app.validation.checks import _histogram_overlap, build_report

client = TestClient(app)


def _one_table(*cols: ColumnSchema, rules=()) -> DatasetSchema:
    columns = [ColumnSchema(name="row_id", data_type="string", semantic_type="id", unique=True), *cols]
    return DatasetSchema(name="t", source="template", tables=[TableSchema(name="things", primary_key="row_id", columns=columns)], rules=list(rules))


def _generate(body_overrides: dict):
    body = {"schema": finance.build().model_dump(by_alias=True), "rows": {"customers": 10}}
    body.update(body_overrides)
    return client.post("/api/generate", json=body)


# --- request admission -----------------------------------------------------------


@pytest.mark.parametrize(
    "override",
    [
        {"seed": -1},
        {"rows": {"customers": 0}},
        {"rows": {"customers": -5}},
        {"rows": {"ghosts": 10}},
        {"rows": {"invoices": 10}},  # child table
        {"locale": "xx_NOPE"},
    ],
)
def test_bad_generate_requests_are_422(override):
    r = _generate(override)
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_schema", r.text


def test_empty_and_broken_schemas_are_422():
    empty = DatasetSchema(name="e", source="template", tables=[])
    assert _generate({"schema": empty.model_dump(by_alias=True), "rows": {}}).status_code == 422

    schema = finance.build()
    schema.rules.append(Rule(id="r9", kind="sum_of_children", table="invoices", column="total",
                             params={"child_table": "invoice_items", "expr": "description"}))
    r = _generate({"schema": schema.model_dump(by_alias=True)})
    assert r.status_code == 422 and "r9" in r.json()["error"]["message"]

    schema = finance.build()
    schema.tables[1].foreign_keys[0].ref_table = "ghosts"
    assert _generate({"schema": schema.model_dump(by_alias=True)}).status_code == 422


def test_total_cells_limit(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "max_total_cells", 1000)
    r = _generate({"rows": {"customers": 500}})
    assert r.status_code == 422 and r.json()["error"]["code"] == "rows_limit_exceeded"


def test_ai_rule_summing_a_text_column_is_dropped():
    draft = SchemaDraft(
        name="shop",
        tables=[
            DraftTable(name="orders", primary_key="order_id", columns=[
                DraftColumn(name="order_id", data_type="string", semantic_type="id"),
                DraftColumn(name="total", data_type="decimal", semantic_type="currency_amount"),
            ]),
            DraftTable(name="items", primary_key="item_id", columns=[
                DraftColumn(name="item_id", data_type="string", semantic_type="id"),
                DraftColumn(name="order_id", data_type="string", semantic_type="id"),
                DraftColumn(name="memo", data_type="string", semantic_type="text"),
            ], foreign_keys=[DraftForeignKey(column="order_id", ref_table="orders", ref_column="order_id")]),
        ],
        rules=[DraftRule(kind="sum_of_children", table="orders", column="total", child_table="items", expr="memo")],
    )
    schema, notes = draft_to_schema(draft)
    assert schema.rules == [] and any("memo" in n for n in notes)


def test_null_burst_on_a_key_is_dropped_but_required_columns_are_allowed():
    plan = ScenarioPlan(proposals=[
        DraftScenario(kind="null_burst", table="customers", column="customer_id", title="bad"),
        DraftScenario(kind="null_burst", table="invoices", column="customer_id", title="fk"),
        DraftScenario(kind="null_burst", table="customers", column="email", title="missing emails"),
    ])
    kept = validate_proposals(plan, finance.build())
    assert [(p.table, p.column) for p in kept] == [("customers", "email")]


# --- uniqueness --------------------------------------------------------------------


def test_impossible_unique_domain_is_rejected():
    schema = _one_table(ColumnSchema(name="code", data_type="integer", semantic_type="generic_number", unique=True, min=0, max=1))
    with pytest.raises(InvalidSchema):
        generator.generate(schema, {"things": 10}, seed=1)
    r = client.post("/api/generate", json={"schema": schema.model_dump(by_alias=True), "rows": {"things": 10}})
    assert r.status_code == 422 and "code" in r.json()["error"]["message"]


@pytest.mark.parametrize(
    "col",
    [
        ColumnSchema(name="code", data_type="integer", semantic_type="generic_number", unique=True, min=0, max=60),
        ColumnSchema(name="price", data_type="decimal", semantic_type="currency_amount", unique=True, min=1, max=2),
        ColumnSchema(name="ratio", data_type="float", semantic_type="generic_number", unique=True, min=0, max=1),
        ColumnSchema(name="day", data_type="date", semantic_type="date", unique=True, min="2024-01-01", max="2024-03-31"),
        ColumnSchema(name="tier", data_type="string", semantic_type="category", unique=True, allowed_values=[f"t{i}" for i in range(80)]),
        ColumnSchema(name="ext", data_type="integer", semantic_type="generic_number", unique=True, min=1),  # no max: extended
    ],
)
def test_unique_columns_are_distinct_and_in_range(col):
    schema = _one_table(col)
    t = generator.generate(schema, {"things": 50}, seed=2)
    s = t["things"][col.name]
    assert s.is_unique
    report = build_report(schema, t)
    assert report.overall == "PASS", [c for c in report.checks if c.status == "FAIL"]


def test_sqlite_unique_constraints_are_preserved():
    import os
    import sqlite3
    import tempfile

    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    db = sqlite3.connect(path)
    db.executescript(
        "CREATE TABLE things (id INTEGER PRIMARY KEY, external_code INTEGER UNIQUE NOT NULL, name TEXT);"
        + "".join(f"INSERT INTO things VALUES ({i}, {100 + i}, 'n{i}');" for i in range(30))
    )
    db.close()
    content = open(path, "rb").read()
    os.remove(path)
    r = client.post("/api/schema/from-sqlite", files={"file": ("x.sqlite", io.BytesIO(content), "application/octet-stream")},
                    data={"mode": "schema_and_sample"})
    assert r.status_code == 200, r.text
    schema = DatasetSchema.model_validate(r.json()["schema"])
    col = next(c for c in schema.tables[0].columns if c.name == "external_code")
    assert col.unique and col.max is None
    # more rows than the 30 sampled values: the range is extended, not violated
    t = generator.generate(schema, {"things": 500}, seed=1)
    assert t["things"]["external_code"].is_unique


# --- rule order ----------------------------------------------------------------------


def test_chained_date_rules_all_hold():
    cols = [ColumnSchema(name=n, data_type="date", semantic_type="date") for n in ("a", "b", "c")]
    rules = [
        Rule(id="r1", kind="date_order", table="things", column="c", params={"before": "b", "after": "c"}),
        Rule(id="r2", kind="date_order", table="things", column="b", params={"before": "a", "after": "b"}),
        Rule(id="r3", kind="date_order", table="things", column="c", params={"before": "a", "after": "c"}),
    ]
    schema = _one_table(*cols, rules=rules)
    t = generator.generate(schema, {"things": 100}, seed=1)
    report = build_report(schema, t)
    assert report.overall == "PASS", [c for c in report.checks if c.status == "FAIL"]


# --- numbers, booleans, categories -----------------------------------------------------


def test_tiny_floats_keep_their_precision():
    values = pd.Series([0.00001, 0.00002, 0.00003] * 5)
    prof = profile_column(values, "float", pii=False)
    assert prof.histogram[0][0] == pytest.approx(0.00001) and prof.histogram[-1][1] == pytest.approx(0.00003)
    assert _histogram_overlap(prof.histogram, values) == pytest.approx(1.0)

    col = ColumnSchema(name="rate", data_type="float", semantic_type="generic_number", min=0.00001, max=0.00003, profile=prof)
    t = generator.generate(_one_table(col), {"things": 500}, seed=1)
    rate = t["things"]["rate"]
    assert (rate > 0).all() and rate.between(0.00001, 0.00003).all()


def test_money_rounding_stays_inside_bounds():
    col = ColumnSchema(name="fee", data_type="decimal", semantic_type="currency_amount", min=0.005, max=0.019)
    fee = generator.generate(_one_table(col), {"things": 2000}, seed=1)["things"]["fee"]
    assert fee.between(0.005, 0.019).all()


def test_yes_no_booleans_profile_and_compare_consistently():
    raw = pd.Series(["yes"] * 8 + ["no"] * 2)
    col = column_from_values("active", raw)
    assert col.data_type == "boolean"
    assert dict(col.profile.top_values) == {"true": 0.8, "false": 0.2}
    schema = _one_table(col)
    t = generator.generate(schema, {"things": 2000}, seed=1)
    assert 0.75 < t["things"]["active"].mean() < 0.85
    assert build_report(schema, t).similarity.overall > 0.95


def test_all_false_profile_generates_false():
    assert generator._true_share([("false", 1.0)]) == 0.0
    assert generator._true_share([("False", 1.0)]) == 0.0
    assert generator._true_share(None) == 0.5


def test_low_cardinality_text_keeps_the_source_values():
    """city/country/company with few distinct sampled values follow the sample, not Faker."""
    cities = pd.Series(["Lahore"] * 6 + ["Berlin"] * 3 + ["Milan"])
    col = column_from_values("city", cities)
    assert col.semantic_type == "city" and col.profile.top_values
    schema = _one_table(col)
    t = generator.generate(schema, {"things": 2000}, seed=1)
    assert set(t["things"]["city"]) == {"Lahore", "Berlin", "Milan"}
    assert build_report(schema, t).similarity.overall > 0.95
    # PII columns never reuse sampled values
    email = column_from_values("email", pd.Series(["a@x.com", "b@x.com"] * 5))
    assert email.pii and not (email.profile and email.profile.top_values)


def test_eleven_categories_are_not_truncated_into_a_rule():
    statuses = [f"status_{i:02d}" for i in range(11)]
    csv = "item_id,status\n" + "".join(f"I{i},{statuses[i % 11]}\n" for i in range(55))
    r = client.post("/api/schema/from-csv", files=[("files", ("items.csv", io.BytesIO(csv.encode()), "text/csv"))])
    assert r.status_code == 200, r.text
    schema = r.json()["schema"]
    col = next(c for c in schema["tables"][0]["columns"] if c["name"] == "status")
    assert col["allowed_values"] in (None, statuses) or set(col["allowed_values"]) == set(statuses)
    for rule in schema["rules"]:
        if rule["kind"] == "allowed_values":
            assert set(rule["params"]["values"]) == set(statuses)


# --- privacy ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["diagnosis_notes", "field_x", "status"])
def test_free_text_never_reaches_the_ai_payload(name):
    secret = "Patient Alice Smith, HIV positive"
    col = column_from_values(name, pd.Series([secret] * 5 + ["Patient Bob Jones, diabetic"] * 5))
    schema = _one_table(col)
    assert secret not in str(build_ai_payload(schema))


def test_short_category_labels_are_still_shared():
    col = column_from_values("status", pd.Series(["paid", "sent", "overdue"] * 10))
    assert build_ai_payload(_one_table(col))[0]["columns"][0]["categories"]


# --- limits ------------------------------------------------------------------------------


def test_store_is_bounded_by_cells(monkeypatch):
    from app.core.config import get_settings

    store.clear()
    monkeypatch.setattr(get_settings(), "max_store_cells", 250)
    report = ValidationReport(overall="PASS")
    schema = _one_table()
    for i in range(3):
        df = pd.DataFrame({"row_id": np.arange(100)})  # 100 cells each
        store.save_dataset(GeneratedDataset(dataset_id=f"ds_{i}", schema=schema, tables={"things": df}, report=report))
    assert [k for k in store._datasets] == ["ds_1", "ds_2"]
    store.clear()


def test_oversized_upload_is_rejected_while_reading(monkeypatch):
    import app.api.schema as schema_api

    monkeypatch.setattr(schema_api, "MAX_FILE_BYTES", 10)
    r = client.post("/api/schema/from-csv", files=[("files", ("big.csv", io.BytesIO(b"a,b\n" + b"1,2\n" * 50), "text/csv"))])
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_csv"
