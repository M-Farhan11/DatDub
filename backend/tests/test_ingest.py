"""F3/F4: CSV + SQLite + Postgres ingest, profiler, AI payload privacy, DB guard."""

import io
import logging
import os
import sqlite3
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.ai.providers.mock import MockProvider
from app.core.config import Settings
from app.engine import store
from app.ingest import db_guard
from app.ingest.db_guard import DbError, build_url, is_public_ip, resolve_host
from app.ingest.enrich import build_ai_payload
from app.main import app
from app.schemas import FromDbResponse, GenerateResponse, SchemaResponse
from app.schemas.api import DbConnection

client = TestClient(app)
PASSWORD = "s3cr3t-pw"


@pytest.fixture(autouse=True)
def _clean_store():
    store.clear()
    yield
    store.clear()


@pytest.fixture
def private_hosts_blocked(monkeypatch):
    monkeypatch.setattr(db_guard, "get_settings", lambda: Settings(allow_private_db_hosts=False))


@pytest.fixture
def private_hosts_allowed(monkeypatch):
    monkeypatch.setattr(db_guard, "get_settings", lambda: Settings(allow_private_db_hosts=True))


# --- fixtures: a small finance dataset --------------------------------------------


def finance_csvs() -> list[tuple[str, bytes]]:
    customers = "customer_id,full_name,email,phone,segment,signup_date\n" + "".join(
        f"C{i},Person {i},user{i}@mail.com,+1 555 010{i % 10} 22{i % 10},{['retail', 'sme', 'corp'][i % 3]},2024-0{1 + i % 9}-1{i % 9}\n"
        for i in range(30)
    )
    invoices = "invoice_id,customer_id,issue_date,due_date,status,total\n"
    items = "item_id,invoice_id,description,quantity,unit_price\n"
    payments = "payment_id,invoice_id,amount,paid_at\n"
    k = 0
    for i in range(60):
        total = 0.0
        for j in range(1 + i % 3):
            qty, price = 1 + j, 10.5 + j
            total += qty * price
            items += f"IT{k},INV{i},Service {k},{qty},{price}\n"
            k += 1
        invoices += f"INV{i},C{i % 30},2024-02-{1 + i % 20:02d},2024-03-{1 + i % 20:02d},{['paid', 'open'][i % 2]},{total:.2f}\n"
        payments += f"P{i},INV{i},{total / 2:.2f},2024-03-{1 + i % 20:02d}\n"
    return [
        ("customers.csv", customers.encode()),
        ("invoices.csv", invoices.encode()),
        ("invoice_items.csv", items.encode()),
        ("payments.csv", payments.encode()),
    ]


def _upload(files: list[tuple[str, bytes]]):
    return client.post("/api/schema/from-csv", files=[("files", (n, io.BytesIO(b), "text/csv")) for n, b in files])


def sqlite_bytes() -> bytes:
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        db = sqlite3.connect(path)
        db.executescript(
            """
            CREATE TABLE customers (customer_id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT, country TEXT);
            CREATE TABLE orders (order_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                                 order_date DATE, status TEXT, total NUMERIC(10,2));
            CREATE TABLE order_items (item_id INTEGER PRIMARY KEY, order_id TEXT REFERENCES orders(order_id),
                                      quantity INTEGER, unit_price NUMERIC(10,2));
            CREATE TABLE audit_log (a INTEGER, b INTEGER, note TEXT, PRIMARY KEY (a, b));
            """
        )
        db.executemany("INSERT INTO customers VALUES (?,?,?,?)",
                       [(f"C{i}", f"Name {i}", f"c{i}@shop.com", ["PK", "UK", "DE"][i % 3]) for i in range(20)])
        db.executemany("INSERT INTO orders VALUES (?,?,?,?,?)",
                       [(f"O{i}", f"C{i % 20}", f"2024-01-{1 + i % 28:02d}", ["new", "shipped"][i % 2], 10.0 * i) for i in range(50)])
        db.executemany("INSERT INTO order_items VALUES (?,?,?,?)", [(i, f"O{i % 50}", 1 + i % 4, 9.99) for i in range(120)])
        db.commit()
        db.close()
        with open(path, "rb") as f:
            return f.read()
    finally:
        os.remove(path)


# --- CSV ----------------------------------------------------------------------------


def test_csv_infers_types_keys_rules_and_profiles():
    res = _upload(finance_csvs())
    assert res.status_code == 200, res.text
    body = SchemaResponse.model_validate(res.json())
    schema = body.schema_
    assert schema.source == "csv"
    assert {t.name for t in schema.tables} == {"customers", "invoices", "invoice_items", "payments"}

    customers = schema.table("customers")
    assert customers.primary_key == "customer_id"
    cols = {c.name: c for c in customers.columns}
    assert cols["email"].semantic_type == "email" and cols["email"].pii
    assert cols["phone"].semantic_type == "phone" and cols["phone"].pii
    assert cols["full_name"].pii
    assert cols["signup_date"].data_type == "date"
    assert cols["segment"].allowed_values and set(cols["segment"].allowed_values) == {"retail", "sme", "corp"}
    # a profile is attached; PII columns never carry sampled values
    assert cols["segment"].profile.top_values
    assert cols["email"].profile is not None and cols["email"].profile.top_values is None

    invoices = schema.table("invoices")
    fk = invoices.foreign_keys[0]
    assert (fk.column, fk.ref_table, fk.ref_column) == ("customer_id", "customers", "customer_id")
    assert fk.children_distribution == [(2, 1.0)]
    total = next(c for c in invoices.columns if c.name == "total")
    assert total.data_type == "decimal" and total.semantic_type == "currency_amount"
    assert total.profile.histogram and len(total.profile.histogram) == 10

    kinds = {(r.kind, r.table, r.column) for r in schema.rules}
    assert ("sum_of_children", "invoices", "total") in kinds
    assert ("lte_parent", "payments", "amount") in kinds
    assert ("date_order", "invoices", "due_date") in kinds
    assert schema.document_hints and schema.document_hints.invoice.header_table == "invoices"


def test_csv_schema_generates_a_valid_dataset():
    schema = _upload(finance_csvs()).json()["schema"]
    res = client.post("/api/generate", json={"schema": schema, "rows": {"customers": 40}, "seed": 3})
    assert res.status_code == 200, res.text
    body = GenerateResponse.model_validate(res.json())
    assert body.report.overall == "PASS"
    assert body.row_counts["invoices"] == 80  # exactly 2 invoices per customer, as in the sample


def test_csv_messy_values():
    csv = (
        "ID,Product Code,Price,Active,Created\n"
        '1,00123,"$1,200.50",yes,01/02/2024\n'
        '2,00456,$15.00,no,02/03/2024\n'
        '3,00789,"$3,000.00",yes,03/04/2024\n'
    ).encode()
    schema = SchemaResponse.model_validate(_upload([("My Products.csv", csv)]).json()).schema_
    t = schema.tables[0]
    assert t.name == "my_products" and t.primary_key == "id"
    cols = {c.name: c for c in t.columns}
    assert cols["product_code"].data_type == "string"  # leading zeros stay a code
    assert cols["price"].data_type == "decimal" and cols["price"].profile.max == 3000.0 and cols["price"].profile.min == 15.0
    assert cols["active"].data_type == "boolean"
    assert cols["created"].data_type == "date"


def test_csv_without_key_gets_generated_pk():
    csv = b"name,score\nA,1\nB,2\nA,3\n"
    res = _upload([("scores.csv", csv)])
    assert res.status_code == 200
    body = SchemaResponse.model_validate(res.json())
    assert body.schema_.tables[0].primary_key == "score_id"
    assert any("no primary key" in n for n in body.notes)


@pytest.mark.parametrize(
    "content",
    [b"", b"   \n", b"a,b\n"],
    ids=["empty", "blank", "header-only"],
)
def test_bad_csv_is_clean_400(content):
    res = _upload([("bad.csv", content)])
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "invalid_csv"


def test_ai_payload_never_contains_pii_values(monkeypatch):
    """Low-cardinality PII (3 repeated emails/names) must not reach the AI; non-PII categories may."""
    csv = "user_id,email,full_name,plan\n" + "".join(
        f"U{i},{['alice@corp.com', 'bob@corp.com', 'carol@corp.com'][i % 3]},"
        f"{['Alice Smith', 'Bob Jones', 'Carol White'][i % 3]},{['free', 'pro'][i % 2]}\n"
        for i in range(30)
    )
    captured = []

    class SpyService:
        async def generate_structured(self, prompt, response_model):
            captured.append(prompt.system + prompt.user + repr(prompt.context))
            return response_model.model_validate_json(await MockProvider().generate_json(prompt, response_model))

    monkeypatch.setattr("app.ingest.enrich.get_ai_service", lambda: SpyService())
    res = _upload([("users.csv", csv.encode())])
    assert res.status_code == 200
    assert len(captured) == 1
    sent = captured[0]
    for value in ("alice@corp.com", "bob@corp.com", "Alice Smith", "Bob Jones", "U1", "U2"):
        assert value not in sent
    assert "free" in sent and "pro" in sent  # non-PII categories are allowed
    # and the response itself carries no sampled PII values either
    for value in ("alice@corp.com", "Alice Smith"):
        assert value not in res.text


def test_ai_unavailable_falls_back_to_heuristics(monkeypatch):
    from app.core.exceptions import AIProviderError

    class DownService:
        async def generate_structured(self, prompt, response_model):
            raise AIProviderError("down")

    monkeypatch.setattr("app.ingest.enrich.get_ai_service", lambda: DownService())
    res = _upload(finance_csvs())
    assert res.status_code == 200
    assert any("heuristics" in n for n in res.json()["notes"])


def test_build_ai_payload_skips_keys_and_pii_stats():
    schema = SchemaResponse.model_validate(_upload(finance_csvs()).json()).schema_
    payload = {t["name"]: {c["name"]: c for c in t["columns"]} for t in build_ai_payload(schema)}
    assert "customer_id" not in payload["customers"] and "customer_id" not in payload["invoices"]
    assert "stats" not in payload["customers"]["email"]
    assert payload["customers"]["segment"]["categories"]
    assert payload["invoices"]["total"]["stats"]["max"] > 0


# --- SQLite -------------------------------------------------------------------------


def _sqlite(data: dict, content: bytes | None = None):
    return client.post(
        "/api/schema/from-sqlite",
        files={"file": ("shop.sqlite", io.BytesIO(content if content is not None else sqlite_bytes()), "application/octet-stream")},
        data=data,
    )


def test_sqlite_schema_only_auto_adds_parents():
    res = _sqlite({"mode": "schema_only", "tables": "order_items"})
    assert res.status_code == 200, res.text
    body = FromDbResponse.model_validate(res.json())
    assert body.schema_.source == "sqlite"
    assert set(body.auto_added) == {"orders", "customers"}
    assert body.rows_sampled == 0
    orders = body.schema_.table("orders")
    assert orders.primary_key == "order_id"
    assert orders.foreign_keys[0].ref_table == "customers"
    assert orders.row_count_hint == 50
    assert all(c.profile is None for t in body.schema_.tables for c in t.columns)
    total = next(c for c in orders.columns if c.name == "total")
    assert total.data_type == "decimal"


def test_sqlite_sample_mode_profiles_and_distributions():
    res = _sqlite({"mode": "schema_and_sample", "sample_limit": "25", "tables": ""})
    assert res.status_code == 200, res.text
    body = FromDbResponse.model_validate(res.json())
    names = {t.name for t in body.schema_.tables}
    assert {"customers", "orders", "order_items", "audit_log"} <= names
    assert body.rows_sampled == 20 + 25 + 25  # customers has only 20 rows; audit_log is empty
    customers = body.schema_.table("customers")
    email = next(c for c in customers.columns if c.name == "email")
    assert email.semantic_type == "email" and email.pii and email.profile.top_values is None
    fk = body.schema_.table("orders").foreign_keys[0]
    assert fk.children_distribution  # counted for the sampled customers
    # composite PK → generated key + a note
    assert body.schema_.table("audit_log").primary_key == "audit_log_id"
    assert any("composite primary key" in n for n in body.notes)


def test_sqlite_upload_is_deleted(monkeypatch):
    created = []
    real_mkstemp = tempfile.mkstemp

    def spy(*args, **kwargs):
        fd, path = real_mkstemp(*args, **kwargs)
        created.append(path)
        return fd, path

    monkeypatch.setattr("app.ingest.database.tempfile.mkstemp", spy)
    content = sqlite_bytes()
    assert _sqlite({"mode": "schema_only"}, content).status_code == 200
    assert created and not any(os.path.exists(p) for p in created)


def test_sqlite_rejects_non_sqlite_and_unknown_tables():
    res = _sqlite({"mode": "schema_only"}, b"not a database")
    assert res.status_code == 400 and res.json()["error"]["code"] == "invalid_sqlite_file"
    res = _sqlite({"mode": "schema_only", "tables": "ghosts"})
    assert res.status_code == 404 and res.json()["error"]["code"] == "table_not_found"
    res = _sqlite({"mode": "everything"})
    assert res.status_code == 422


# --- DB guard -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "ip,public",
    [
        ("8.8.8.8", True),
        ("127.0.0.1", False),
        ("10.1.2.3", False),
        ("172.16.0.5", False),
        ("192.168.1.10", False),
        ("169.254.169.254", False),
        ("100.64.0.1", False),
        ("0.0.0.0", False),
        ("::1", False),
        ("fe80::1", False),
        ("fd00::1", False),
        ("::ffff:127.0.0.1", False),
        ("2606:4700:4700::1111", True),
    ],
)
def test_is_public_ip(ip, public):
    assert is_public_ip(ip) is public


@pytest.mark.parametrize("host", ["127.0.0.1", "169.254.169.254", "localhost", "10.0.0.8"])
def test_private_hosts_rejected(private_hosts_blocked, host):
    with pytest.raises(DbError) as exc:
        resolve_host(host, 5432)
    assert exc.value.code == "db_host_not_allowed"


def test_private_host_allowed_in_local_dev(private_hosts_allowed):
    assert resolve_host("127.0.0.1", 5432) == "127.0.0.1"


@pytest.mark.parametrize(
    "url,code",
    [
        ("mysql://u:p@db.example.com/x", "db_unsupported_dialect"),
        ("sqlite:///etc/passwd", "db_unsupported_dialect"),
        ("postgresql://u:p@db.example.com/x?host=127.0.0.1", "db_unsupported_dialect"),
        ("postgresql://u:p@db.example.com/x?hostaddr=169.254.169.254", "db_unsupported_dialect"),
        ("postgresql://u:p@db.example.com/x?sslmode=bogus", "db_unsupported_dialect"),
        ("postgresql://u:p@db.example.com", "db_unsupported_dialect"),
        ("not a url", "db_unsupported_dialect"),
    ],
)
def test_build_url_rejects(url, code):
    with pytest.raises(DbError) as exc:
        build_url(DbConnection(url=url))
    assert exc.value.code == code


def test_build_url_from_fields_and_url():
    url = build_url(DbConnection(host="db.example.com", database="postgres", user="ro", password=PASSWORD, sslmode="require"))
    assert url.drivername == "postgresql+psycopg" and url.query == {"sslmode": "require"} and url.port == 5432
    url = build_url(DbConnection(url=f"postgres://ro:{PASSWORD}@db.example.com:6543/app?sslmode=require"))
    assert url.port == 6543 and url.database == "app"


@pytest.mark.parametrize("endpoint", ["/api/db/tables", "/api/schema/from-db"])
@pytest.mark.parametrize("host", ["127.0.0.1", "169.254.169.254"])
def test_api_blocks_private_hosts_without_leaking(private_hosts_blocked, caplog, endpoint, host):
    conn = {"url": f"postgresql://reader:{PASSWORD}@{host}:5432/postgres"}
    with caplog.at_level(logging.DEBUG):
        res = client.post(endpoint, json={"connection": conn, "tables": ["t"]})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "db_host_not_allowed"
    assert PASSWORD not in res.text and PASSWORD not in caplog.text


def test_unreachable_db_is_clean_error_without_leaking(private_hosts_allowed, caplog):
    # port 1 on localhost: connection refused immediately
    conn = {"host": "127.0.0.1", "port": 1, "database": "postgres", "user": "reader", "password": PASSWORD}
    with caplog.at_level(logging.DEBUG):
        res = client.post("/api/db/tables", json={"connection": conn})
    assert res.status_code == 400
    assert res.json()["error"]["code"] in ("db_unreachable", "db_timeout")
    assert PASSWORD not in res.text and PASSWORD not in caplog.text


def test_unresolvable_host(private_hosts_blocked):
    res = client.post("/api/db/tables", json={"connection": {"url": f"postgresql://u:{PASSWORD}@no-such-host.invalid/db"}})
    assert res.status_code == 400 and res.json()["error"]["code"] == "db_unreachable"
    assert PASSWORD not in res.text


# --- Postgres (only when TEST_PG_URL points at a database you can create tables in) ---

PG_URL = os.environ.get("TEST_PG_URL")


@pytest.mark.skipif(not PG_URL, reason="set TEST_PG_URL=postgresql://user:pass@localhost:5432/db to run")
def test_postgres_end_to_end(private_hosts_allowed):
    from sqlalchemy import create_engine, text

    admin = create_engine("postgresql+psycopg://" + PG_URL.split("://", 1)[1])
    with admin.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS f3_orders, f3_customers"))
        c.execute(text("CREATE TABLE f3_customers (customer_id text PRIMARY KEY, email text, tier text)"))
        c.execute(text("CREATE TABLE f3_orders (order_id text PRIMARY KEY, customer_id text REFERENCES f3_customers, "
                       "placed_at timestamp, total numeric(10,2))"))
        c.execute(text("INSERT INTO f3_customers SELECT 'C'||g, 'u'||g||'@x.com', (ARRAY['gold','silver'])[1+g%2] "
                       "FROM generate_series(1,40) g"))
        c.execute(text("INSERT INTO f3_orders SELECT 'O'||g, 'C'||(1+g%40), now() - g * interval '1 day', g*1.5 "
                       "FROM generate_series(1,100) g"))
        c.execute(text("ANALYZE f3_customers; ANALYZE f3_orders"))
    try:
        conn = {"url": PG_URL}
        res = client.post("/api/db/tables", json={"connection": conn})
        assert res.status_code == 200, res.text
        info = {t["name"]: t for t in res.json()["tables"]}
        assert info["f3_orders"]["references"] == ["f3_customers"]
        assert info["f3_orders"]["estimated_rows"] == 100

        res = client.post("/api/schema/from-db",
                          json={"connection": conn, "tables": ["f3_orders"], "mode": "schema_and_sample", "sample_limit": 30})
        assert res.status_code == 200, res.text
        body = FromDbResponse.model_validate(res.json())
        assert body.auto_added == ["f3_customers"] and body.rows_sampled == 60
        assert body.schema_.table("f3_orders").foreign_keys[0].children_distribution
        pw = PG_URL.split(":")[2].split("@")[0]
        assert pw not in res.text
    finally:
        with admin.begin() as c:
            c.execute(text("DROP TABLE IF EXISTS f3_orders, f3_customers"))
        admin.dispose()
