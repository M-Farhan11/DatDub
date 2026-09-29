"""H6: invoice PDFs. OWNER: Haider.

Acceptance: the total printed on an invoice equals the sum of its line items
in the generated data (unless a scenario broke that rule on purpose, in which
case the PDF shows both the subtotal and the stored total).
"""

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.documents.invoice_data import extract_invoice
from app.documents.invoice_pdf import invoice_pdf_bytes, money
from app.engine import store
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_store():
    store.clear()
    yield
    store.clear()


def _template(tid: str = "finance") -> dict:
    return client.get(f"/api/templates/{tid}").json()


def _generate(tid: str = "finance", customers: int = 20, scenarios: list | None = None) -> dict:
    res = client.post(
        "/api/generate",
        json={"schema": _template(tid), "rows": {"customers": customers}, "seed": 42, "scenarios": scenarios or []},
    )
    assert res.status_code == 200, res.text
    return res.json()


def _invoice_ids(dataset_id: str) -> list[str]:
    res = client.get(f"/api/datasets/{dataset_id}/documents/invoices")
    assert res.status_code == 200
    return res.json()["invoice_ids"]


def test_invoice_pdf_endpoint_returns_a_pdf():
    ds = _generate()["dataset_id"]
    invoice_id = _invoice_ids(ds)[0]
    res = client.get(f"/api/datasets/{ds}/documents/invoices/{invoice_id}.pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert f'filename="{invoice_id}.pdf"' in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF")


def test_every_invoice_total_equals_the_sum_of_its_items():
    ds_id = _generate(customers=40)["dataset_id"]
    dataset = store.get_dataset(ds_id)
    items = dataset.tables["invoice_items"]
    invoices = dataset.tables["invoices"].set_index("invoice_id")
    for invoice_id in _invoice_ids(ds_id):
        data = extract_invoice(dataset, invoice_id)
        lines = items[items["invoice_id"] == invoice_id]
        expected = round(float((lines["quantity"] * pd.to_numeric(lines["unit_price"])).sum()), 2)
        assert len(data.items) == len(lines)
        assert data.subtotal == pytest.approx(expected, abs=0.005)
        assert data.total == pytest.approx(float(invoices.loc[invoice_id, "total"]), abs=0.005)
        assert data.total == pytest.approx(data.subtotal, abs=0.005), invoice_id


def test_pdf_prints_the_reconciled_total_and_billed_to():
    ds_id = _generate()["dataset_id"]
    dataset = store.get_dataset(ds_id)
    invoice_id = _invoice_ids(ds_id)[0]
    data = extract_invoice(dataset, invoice_id)
    pdf = invoice_pdf_bytes(dataset, invoice_id, compress=False)
    assert f"Total: {money(data.total, data.currency)}".encode() in pdf
    assert data.billed_to and data.billed_to[0].encode("latin-1", "ignore") in pdf
    assert b"Not a real invoice" in pdf


def test_same_dataset_gives_identical_pdf_bytes():
    ds_id = _generate()["dataset_id"]
    invoice_id = _invoice_ids(ds_id)[0]
    url = f"/api/datasets/{ds_id}/documents/invoices/{invoice_id}.pdf"
    assert client.get(url).content == client.get(url).content


def test_injected_rule_violation_shows_subtotal_next_to_total():
    proposal = {
        "id": "t1",
        "kind": "rule_violation",
        "table": "invoices",
        "column": "total",
        "rule_id": "r1",
        "title": "Invoice total does not match its items",
        "suggested_count": 2,
        "description": "Totals that differ from the sum of the line items.",
        "expected_behavior": "Reconciliation flags the invoice.",
    }
    body = _generate(scenarios=[{"proposal": proposal, "count": 2}])
    broken = next(g for g in body["ground_truth"] if g["scenario_id"] == "t1")["affected_ids"]
    dataset = store.get_dataset(body["dataset_id"])
    data = extract_invoice(dataset, broken[0])
    assert data.total != pytest.approx(data.subtotal, abs=0.005)
    pdf = invoice_pdf_bytes(dataset, broken[0], compress=False)
    assert b"Subtotal" in pdf
    assert money(data.subtotal, data.currency).encode() in pdf


def test_schema_without_invoice_hints_has_no_documents():
    ds_id = _generate("ecommerce")["dataset_id"]
    res = client.get(f"/api/datasets/{ds_id}/documents/invoices/ORD-00001.pdf")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "no_documents"


def test_unknown_invoice_and_unknown_dataset():
    ds_id = _generate()["dataset_id"]
    res = client.get(f"/api/datasets/{ds_id}/documents/invoices/INV-99999.pdf")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "invoice_not_found"
    res = client.get("/api/datasets/ds_missing/documents/invoices/INV-00001.pdf")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "dataset_not_found"
