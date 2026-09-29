"""F0: every endpoint returns contract-valid JSON."""

import io

import pytest
from fastapi.testclient import TestClient

from app.engine import store
from app.main import app
from app.schemas import (
    DatasetSchema,
    DbTablesResponse,
    FromDbResponse,
    GenerateResponse,
    ProposeScenariosResponse,
    SchemaResponse,
    TablePage,
    TemplateSummary,
)

client = TestClient(app)
CONN = {"url": "postgresql://reader:s3cr3t-pw@db.example.com:5432/postgres"}


@pytest.fixture(autouse=True)
def _clean_store():
    store.clear()
    yield
    store.clear()


def _template(tid: str = "finance") -> dict:
    return client.get(f"/api/templates/{tid}").json()


def test_templates_list_and_get():
    res = client.get("/api/templates")
    assert res.status_code == 200
    ids = {TemplateSummary.model_validate(t).id for t in res.json()}
    assert ids == {"finance", "ecommerce"}
    for tid in ids:
        DatasetSchema.model_validate(_template(tid))


def test_unknown_template_is_error_envelope():
    res = client.get("/api/templates/nope")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "template_not_found"


def test_from_prompt_and_csv():
    res = client.post("/api/schema/from-prompt", json={"prompt": "An online shop"})
    assert res.status_code == 200
    assert SchemaResponse.model_validate(res.json()).schema_.source == "prompt"

    files = [("files", ("customers.csv", io.BytesIO(b"id,email\n1,a@b.c\n"), "text/csv"))]
    res = client.post("/api/schema/from-csv", files=files)
    assert res.status_code == 200
    SchemaResponse.model_validate(res.json())


def test_db_endpoints_never_echo_password():
    res = client.post("/api/db/tables", json={"connection": CONN})
    assert res.status_code == 200
    DbTablesResponse.model_validate(res.json())
    assert "s3cr3t-pw" not in res.text

    res = client.post(
        "/api/schema/from-db",
        json={"connection": CONN, "tables": ["payments"], "mode": "schema_and_sample", "sample_limit": 100},
    )
    assert res.status_code == 200
    body = FromDbResponse.model_validate(res.json())
    assert set(body.auto_added) == {"invoices", "customers"}
    assert "s3cr3t-pw" not in res.text

    # invalid request: the error must not echo the password either
    res = client.post("/api/schema/from-db", json={"connection": {"password": "s3cr3t-pw"}, "tables": []})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"
    assert "s3cr3t-pw" not in res.text


def test_from_sqlite():
    res = client.post(
        "/api/schema/from-sqlite",
        files={"file": ("demo.sqlite", io.BytesIO(b"x"), "application/octet-stream")},
        data={"mode": "schema_only", "tables": "invoices"},
    )
    assert res.status_code == 200
    assert FromDbResponse.model_validate(res.json()).auto_added == ["customers"]


def test_propose_scenarios():
    res = client.post("/api/scenarios/propose", json={"schema": _template(), "instruction": "edge cases"})
    assert res.status_code == 200
    proposals = ProposeScenariosResponse.model_validate(res.json()).proposals
    assert proposals and {p.kind for p in proposals} <= {
        "rule_violation", "null_burst", "extreme_value", "duplicate_record", "boundary_date"
    }
    table_names = {t["name"] for t in _template()["tables"]}
    assert all(p.table in table_names for p in proposals)


def test_generate_preview_page_and_documents():
    res = client.post("/api/generate", json={"schema": _template(), "rows": {"customers": 50}, "seed": 7})
    assert res.status_code == 200
    body = GenerateResponse.model_validate(res.json())
    assert body.row_counts["customers"] == 50
    assert body.report.overall == "PASS"
    assert all(len(rows) <= 50 for rows in body.previews.values())

    ds = store.get_dataset(body.dataset_id)
    inv, items = ds.tables["invoices"], ds.tables["invoice_items"]
    sums = (items["quantity"] * items["unit_price"]).groupby(items["invoice_id"]).sum()
    assert (inv.set_index("invoice_id")["total"] - sums.reindex(inv["invoice_id"]).fillna(0)).abs().max() < 0.01
    assert (inv["due_date"] >= inv["issue_date"]).all()

    res = client.get(f"/api/datasets/{body.dataset_id}/tables/invoices?offset=0&limit=10")
    page = TablePage.model_validate(res.json())
    assert page.total == body.row_counts["invoices"] and len(page.rows) == min(10, page.total)
    assert isinstance(page.rows[0]["issue_date"], str)

    res = client.get(f"/api/datasets/{body.dataset_id}/documents/invoices")
    assert res.status_code == 200 and len(res.json()["invoice_ids"]) == body.row_counts["invoices"]


def test_same_seed_same_output():
    req = {"schema": _template("ecommerce"), "rows": {"customers": 30}, "seed": 1}
    a = client.post("/api/generate", json=req).json()
    b = client.post("/api/generate", json=req).json()
    assert a["previews"] == b["previews"] and a["dataset_id"] != b["dataset_id"]


def test_rows_limit_and_unknown_dataset():
    res = client.post("/api/generate", json={"schema": _template(), "rows": {"customers": 10_000_000}})
    assert res.status_code == 422 and res.json()["error"]["code"] == "rows_limit_exceeded"

    res = client.get("/api/datasets/ds_missing/tables/customers")
    assert res.status_code == 404 and res.json()["error"]["code"] == "dataset_not_found"
