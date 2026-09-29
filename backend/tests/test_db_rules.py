"""F8: rules inferred inside the source database with aggregate queries."""

import io
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.engine import generator
from app.main import app
from app.schemas import DatasetSchema
from app.validation.checks import build_report
from tests.test_ingest import private_hosts_allowed  # noqa: F401  (fixture)

client = TestClient(app)

STATUSES = ["draft", "sent", "paid", "overdue", "void", "disputed", "partial", "refunded"]


def finance_sqlite() -> bytes:
    """Finance DB where every business rule holds: totals = item sums, dates ordered, payments <= totals."""
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        db = sqlite3.connect(path)
        db.executescript(
            """
            CREATE TABLE customers (customer_id TEXT PRIMARY KEY, full_name TEXT NOT NULL, email TEXT UNIQUE,
                                    created_at DATE NOT NULL);
            CREATE TABLE invoices (invoice_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                                   issue_date DATE NOT NULL, due_date DATE NOT NULL, status TEXT NOT NULL,
                                   total NUMERIC(12,2) NOT NULL);
            CREATE TABLE invoice_items (item_id TEXT PRIMARY KEY, invoice_id TEXT NOT NULL REFERENCES invoices(invoice_id),
                                        description TEXT, quantity INTEGER NOT NULL, unit_price NUMERIC(10,2) NOT NULL);
            CREATE TABLE payments (payment_id TEXT PRIMARY KEY, invoice_id TEXT NOT NULL REFERENCES invoices(invoice_id),
                                   amount NUMERIC(12,2) NOT NULL, paid_at DATE NOT NULL);
            """
        )
        for i in range(40):
            db.execute("INSERT INTO customers VALUES (?,?,?,?)", (f"C{i}", f"Person {i}", f"p{i}@mail.com", f"2023-0{1 + i % 6}-01"))
        item = 0
        for i in range(120):
            total = 0.0
            for j in range(1 + i % 3):
                qty, price = 1 + (i + j) % 4, round(12.5 + 3 * j + i % 7, 2)
                total += qty * price
                db.execute("INSERT INTO invoice_items VALUES (?,?,?,?,?)", (f"IT{item}", f"INV{i}", f"Service {item}", qty, price))
                item += 1
            issue = f"2024-0{1 + i % 9}-1{i % 10}"
            due = f"2024-0{1 + i % 9}-2{i % 10}"
            db.execute("INSERT INTO invoices VALUES (?,?,?,?,?,?)",
                       (f"INV{i}", f"C{i % 40}", issue, due, STATUSES[i % len(STATUSES)], round(total, 2)))
            if i % 2 == 0:
                db.execute("INSERT INTO payments VALUES (?,?,?,?)", (f"P{i}", f"INV{i}", round(total * (1 if i % 4 else 0.5), 2), due))
        db.commit()
        db.close()
        with open(path, "rb") as f:
            return f.read()
    finally:
        os.remove(path)


def _extract(mode: str, sample_limit: int = 200):
    r = client.post(
        "/api/schema/from-sqlite",
        files={"file": ("finance.sqlite", io.BytesIO(finance_sqlite()), "application/octet-stream")},
        data={"mode": mode, "sample_limit": str(sample_limit)},
    )
    assert r.status_code == 200, r.text
    return DatasetSchema.model_validate(r.json()["schema"]), r.json()["notes"]


def test_sample_mode_finds_the_finance_rules_and_generation_reconciles():
    schema, notes = _extract("schema_and_sample")
    found = {(r.kind, r.table, r.column) for r in schema.rules}
    assert ("sum_of_children", "invoices", "total") in found
    assert ("date_order", "invoices", "due_date") in found
    assert ("date_order", "invoices", "issue_date") in found  # via the customer FK
    assert ("lte_parent", "payments", "amount") in found
    assert ("allowed_values", "invoices", "status") in found
    total_rule = next(r for r in schema.rules if r.kind == "sum_of_children")
    assert total_rule.params == {"child_table": "invoice_items", "expr": "quantity * unit_price"}
    assert any("aggregate queries" in n for n in notes)
    # the UNIQUE email constraint came through
    assert next(c for c in schema.table("customers").columns if c.name == "email").unique

    tables = generator.generate(schema, {"customers": 200}, seed=3)
    report = build_report(schema, tables)
    assert report.overall == "PASS", [c for c in report.checks if c.status == "FAIL"]
    items = tables["invoice_items"]
    sums = (items["quantity"] * items["unit_price"]).groupby(items["invoice_id"]).sum().round(2)
    inv = tables["invoices"].set_index("invoice_id")
    assert ((inv["total"] - sums.reindex(inv.index).fillna(0)).abs() <= 0.01).all()


def test_schema_only_mode_reads_no_rows_and_infers_no_rules():
    schema, _ = _extract("schema_only")
    assert schema.rules == []


def test_incomplete_sampled_categories_are_not_a_closed_list():
    schema, _ = _extract("schema_and_sample", sample_limit=3)  # 3 rows cannot show all 8 statuses
    status = next(c for c in schema.table("invoices").columns if c.name == "status")
    assert not status.allowed_values
    assert not any(r.kind == "allowed_values" and r.column == "status" for r in schema.rules)


# --- Postgres: the real demo seed ------------------------------------------------------

# A SCRATCH database only: the seed drops and recreates customers, invoices,
# invoice_items and payments in its public schema.
PG_SEED_URL = os.environ.get("TEST_PG_SEED_URL")
SEED_SQL = Path(__file__).resolve().parents[2] / "scripts" / "seed_demo_db.sql"


@pytest.mark.skipif(not PG_SEED_URL, reason="set TEST_PG_SEED_URL=postgresql://user:pass@localhost:5432/scratch_db to run")
def test_postgres_demo_seed_end_to_end(private_hosts_allowed):  # noqa: F811
    import psycopg

    dsn = "postgresql://" + PG_SEED_URL.split("://", 1)[1]
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(SEED_SQL.read_text(encoding="utf-8"))
        for check in (
            "SELECT COUNT(*) FROM invoices i WHERE i.total <> (SELECT COALESCE(SUM(quantity * unit_price), 0) "
            "FROM invoice_items it WHERE it.invoice_id = i.invoice_id)",
            "SELECT COUNT(*) FROM payments p JOIN invoices i USING (invoice_id) WHERE p.amount > i.total OR p.paid_at < i.issue_date",
            "SELECT COUNT(*) FROM invoices i JOIN customers c USING (customer_id) WHERE i.issue_date < c.created_at OR i.due_date < i.issue_date",
        ):
            assert admin.execute(check).fetchone()[0] == 0, check
    try:
        conn = {"url": PG_SEED_URL}
        res = client.post("/api/schema/from-db", json={"connection": conn, "tables": ["payments", "invoice_items"],
                                                        "mode": "schema_and_sample", "sample_limit": 200})
        assert res.status_code == 200, res.text
        body = res.json()
        assert set(body["auto_added"]) == {"invoices", "customers"}
        schema = DatasetSchema.model_validate(body["schema"])
        found = {(r.kind, r.table, r.column) for r in schema.rules}
        assert ("sum_of_children", "invoices", "total") in found
        assert ("lte_parent", "payments", "amount") in found
        assert ("date_order", "invoices", "due_date") in found
        assert ("allowed_values", "invoices", "status") in found
        assert next(c for c in schema.table("customers").columns if c.name == "email").unique
        assert PG_SEED_URL.split(":")[2].split("@")[0] not in res.text  # password never echoed

        r = client.post("/api/generate", json={"schema": body["schema"], "rows": {"customers": 1000}, "seed": 1})
        assert r.status_code == 200, r.text
        report = r.json()["report"]
        assert report["overall"] == "PASS", [c for c in report["checks"] if c["status"] == "FAIL"]
        assert report["similarity"] is not None
    finally:
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute("DROP TABLE IF EXISTS payments, invoice_items, invoices, customers CASCADE")
