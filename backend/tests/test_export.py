"""H7: ZIP export. OWNER: Haider."""

import csv
import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.engine import store
from app.main import app
from app.schemas import DatasetSchema, GroundTruthEntry, ValidationReport

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_store():
    store.clear()
    yield
    store.clear()


def _generate(tid: str = "finance", customers: int = 30, scenarios: list | None = None) -> dict:
    schema = client.get(f"/api/templates/{tid}").json()
    res = client.post(
        "/api/generate",
        json={"schema": schema, "rows": {"customers": customers}, "seed": 42, "scenarios": scenarios or []},
    )
    assert res.status_code == 200, res.text
    return res.json()


def _zip(dataset_id: str) -> zipfile.ZipFile:
    res = client.get(f"/api/datasets/{dataset_id}/export.zip")
    assert res.status_code == 200, res.text
    assert res.headers["content-type"] == "application/zip"
    assert res.headers["content-disposition"].startswith("attachment;")
    assert int(res.headers["content-length"]) == len(res.content)
    return zipfile.ZipFile(io.BytesIO(res.content))


def test_zip_contains_every_expected_file():
    body = _generate()
    zf = _zip(body["dataset_id"])
    names = set(zf.namelist())
    for table in body["row_counts"]:
        assert f"tables/{table}.csv" in names
        assert f"tables/{table}.json" in names
    assert {"schema.json", "validation_report.json", "ground_truth.json", "README.txt"} <= names
    assert zf.testzip() is None  # every member's CRC is valid


def test_tables_match_row_counts_and_previews():
    body = _generate()
    zf = _zip(body["dataset_id"])
    for table, count in body["row_counts"].items():
        rows = list(csv.DictReader(io.StringIO(zf.read(f"tables/{table}.csv").decode("utf-8"))))
        records = json.loads(zf.read(f"tables/{table}.json"))
        assert len(rows) == count == len(records)
        # the JSON matches the API preview exactly (same formatting as /tables paging)
        assert records[: len(body["previews"][table])] == body["previews"][table]
    invoice = json.loads(zf.read("tables/invoices.json"))[0]
    assert len(invoice["issue_date"]) == 10 and invoice["issue_date"][4] == "-"


def test_metadata_files_are_contract_valid():
    proposal = {
        "id": "t1",
        "kind": "rule_violation",
        "table": "payments",
        "column": "amount",
        "rule_id": "r3",
        "title": "Payment exceeds invoice total",
        "suggested_count": 3,
        "description": "Overpayments.",
        "expected_behavior": "Flag the overpayment.",
    }
    body = _generate(scenarios=[{"proposal": proposal, "count": 3}])
    zf = _zip(body["dataset_id"])
    DatasetSchema.model_validate_json(zf.read("schema.json"))
    report = ValidationReport.model_validate_json(zf.read("validation_report.json"))
    assert report.overall == body["report"]["overall"]
    truth = [GroundTruthEntry.model_validate(g) for g in json.loads(zf.read("ground_truth.json"))]
    assert [g.affected_ids for g in truth] == [g["affected_ids"] for g in body["ground_truth"]]
    assert len(truth[0].affected_ids) == 3


def test_first_20_invoices_are_included_as_pdfs():
    body = _generate(customers=30)
    zf = _zip(body["dataset_id"])
    pdfs = sorted(n for n in zf.namelist() if n.startswith("documents/invoices/"))
    assert len(pdfs) == min(20, body["row_counts"]["invoices"])
    assert pdfs[0] == "documents/invoices/INV-00001.pdf"
    assert all(zf.read(n).startswith(b"%PDF") for n in pdfs)


def test_schema_without_invoices_has_no_documents_folder():
    body = _generate("ecommerce")
    zf = _zip(body["dataset_id"])
    assert not any(n.startswith("documents/") for n in zf.namelist())
    assert "invoices" not in zf.read("README.txt").decode()


def test_unknown_dataset_returns_404():
    res = client.get("/api/datasets/ds_missing/export.zip")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "dataset_not_found"
