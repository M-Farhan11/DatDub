# API Contract

Status: **DRAFT v0.1**. Farhan finalizes it in task F0. After F0, any change
needs both people to agree (add it under Requests in `TASKS.md`).

- Base URL: `VITE_API_URL` (local: `http://127.0.0.1:8000`)
- All endpoints are under `/api`. JSON unless noted. No auth.
- Errors: `{"error": {"code": "string", "message": "human readable"}}` with 4xx/5xx.
- The backend source of truth is `backend/app/schemas/`, and the frontend mirror is `frontend/src/api/types.ts`.

## Core model: `DatasetSchema`

```json
{
  "name": "finance_demo",
  "source": "template | prompt | csv | postgres | sqlite",
  "tables": [
    {
      "name": "customers",
      "primary_key": "customer_id",
      "row_count_hint": 200,
      "columns": [
        {
          "name": "email",
          "data_type": "string | integer | float | decimal | boolean | date | datetime",
          "semantic_type": "email",
          "nullable": false,
          "unique": true,
          "pii": true,
          "confidence": 0.96,
          "allowed_values": null,
          "min": null, "max": null,
          "profile": null
        }
      ],
      "foreign_keys": [
        { "column": "customer_id", "ref_table": "customers", "ref_column": "customer_id",
          "cardinality": "1:N", "min_children": 0, "max_children": 10 }
      ]
    }
  ],
  "rules": [
    { "id": "r1", "kind": "sum_of_children", "table": "invoices", "column": "total",
      "params": { "child_table": "invoice_items", "expr": "quantity * unit_price" },
      "description": "Invoice total equals the sum of its line items" }
  ],
  "document_hints": {
    "invoice": { "header_table": "invoices", "items_table": "invoice_items", "party_table": "customers" }
  }
}
```

`semantic_type` values: `id, person_name, first_name, last_name, email, phone, address, city, country, company, date, datetime, currency_amount, quantity, percentage, category, status, text, url, sku, iban, generic_number, generic_string`.

`profile` (only when sample rows were read):
`{ "null_rate": 0.02, "mean": 120.5, "std": 30.1, "min": 1, "max": 900, "histogram": [[0,50,12], ...], "top_values": [["paid",0.6], ...], "unique_ratio": 0.98 }`

### Rule kinds (fixed catalogue)
| kind | params |
|---|---|
| `range` | `{min, max}` on `table.column` |
| `allowed_values` | `{values: [...]}` |
| `date_order` | `{before: "col_a", after: "col_b", via_fk?: "fk_column"}` |
| `sum_of_children` | `{child_table, expr}` (expr = one column or `a * b`) |
| `lte_parent` | `{parent_table, parent_column}` (the child column must be ≤ the parent column) |

### Scenario kinds (fixed catalogue)
`null_burst`, `extreme_value`, `duplicate_record`, `boundary_date`, `rule_violation`

## Endpoints

### `GET /api/health` → `{"status":"ok"}`

### `GET /api/templates` → `[{ "id": "finance", "name": "Finance", "description": "...", "tables": 4 }]`
### `GET /api/templates/{id}` → `DatasetSchema`

### `POST /api/schema/from-prompt`
Req `{ "prompt": "An e-commerce store with customers, orders, items and payments" }`
Res `{ "schema": DatasetSchema, "notes": ["AI assumed payments are 1:N per order"] }`

### `POST /api/schema/from-csv` (multipart, field `files`, 1..n CSV)
Res `{ "schema": DatasetSchema, "notes": [...] }` (columns carry a `profile`)

### Database connection: two steps, no stored connection

`DbConnection` (send **either** `url` **or** the individual fields):
```json
{ "url": "postgresql://user:pass@host:5432/db" }
{ "host": "db.xxxx.supabase.co", "port": 5432, "database": "postgres",
  "user": "readonly_user", "password": "…", "sslmode": "require" }
```
- Only Postgres is accepted (`postgresql://` / `postgres://`). Private, loopback and link-local hosts are rejected when `ALLOW_PRIVATE_DB_HOSTS=false` (the deployed default).
- The backend keeps **no connection between calls**. The frontend holds the credentials in memory only (never in `localStorage`) and re-sends them with each call.
- Credentials are never stored, logged or echoed back.

#### `POST /api/db/tables` (Step A: list tables, reads NO rows)
Req `{ "connection": DbConnection }`
Res
```json
{ "tables": [
  { "name": "customers", "schema": "public", "column_count": 12, "estimated_rows": 48000,
    "references": [] },
  { "name": "invoices", "schema": "public", "column_count": 9, "estimated_rows": 210000,
    "references": ["customers"] }
]}
```
`estimated_rows` comes from Postgres statistics (`pg_class.reltuples`); no `COUNT(*)` is run.

#### `POST /api/schema/from-db` (Steps B+C: extract the selected tables)
Req
```json
{ "connection": DbConnection,
  "tables": ["customers", "invoices"],
  "mode": "schema_only | schema_and_sample",
  "sample_limit": 200 }
```
- `tables`: FK parent tables are **auto-added**, and the response lists them in `auto_added`.
- `sample_limit`: default 200, max 1000 rows per table. Ignored in `schema_only`.
- Sampling uses `TABLESAMPLE SYSTEM` for large tables and `ORDER BY random() LIMIT n` for small ones. It runs inside a read-only transaction with a 10 s `statement_timeout`.
- Sample rows are profiled in memory and then discarded. They are never stored or sent to the AI.

Res `{ "schema": DatasetSchema, "auto_added": ["customers"], "rows_sampled": 400, "notes": [...] }`

Errors: `db_unreachable`, `db_auth_failed`, `db_host_not_allowed`, `db_timeout`, `db_unsupported_dialect` (400/422, with a human-readable message).

### `POST /api/schema/from-sqlite` (multipart: field `file`, form fields `mode`, `sample_limit`, optional `tables`)
Res: same as `from-db`. The uploaded file is deleted after the request.

### `POST /api/scenarios/propose`
Req `{ "schema": DatasetSchema, "instruction": "Add realistic edge cases for testing" }`
Res
```json
{ "proposals": [
  { "id": "s1", "kind": "rule_violation", "table": "payments", "column": "amount",
    "rule_id": "r3", "title": "Payment exceeds invoice total", "suggested_count": 5,
    "description": "...", "expected_behavior": "App should flag overpayment" }
]}
```

### `POST /api/generate`
Req
```json
{
  "schema": DatasetSchema,
  "rows": { "customers": 500 },
  "seed": 42,
  "null_rate": 0.02,
  "outlier_rate": 0.01,
  "locale": "en_US",
  "scenarios": [ { "proposal": { "...ScenarioProposal" }, "count": 5 } ]
}
```
`rows` sets counts for root tables. Child counts come from cardinality.
Limits: each table is capped at `MAX_ROWS_PER_TABLE` (default 100,000),
with a hard ceiling of 500,000 per table. A request above the cap returns
`422 rows_limit_exceeded`. Only 50 preview rows per table are returned; the
full data is available through the paged table endpoint and the ZIP.
Datasets expire after `DATASET_TTL_MINUTES` (60) and at most
`MAX_DATASETS` (20) are kept, oldest evicted first. An expired or unknown
ID returns `404 dataset_not_found`.
Res
```json
{
  "dataset_id": "ds_8f2a",
  "row_counts": { "customers": 500, "invoices": 1480 },
  "previews": { "customers": [ { "customer_id": 1, "...": "..." } ] },
  "report": ValidationReport,
  "ground_truth": [GroundTruthEntry]
}
```

`ValidationReport`
```json
{
  "overall": "PASS | FAIL",
  "checks": [
    { "name": "PK uniqueness", "table": "customers", "status": "PASS", "score": 1.0, "detail": "" },
    { "name": "FK integrity", "table": "invoices", "status": "PASS", "score": 1.0, "detail": "" },
    { "name": "Rule r1", "table": "invoices", "status": "PASS", "score": 1.0,
      "detail": "1480/1480 pass", "expected_violations": 0 }
  ],
  "similarity": { "overall": 0.91, "per_column": { "invoices.total": 0.88 } }
}
```

`GroundTruthEntry`
```json
{ "scenario_id": "s1", "kind": "rule_violation", "table": "payments",
  "affected_ids": ["PAY-0102", "PAY-0103"], "description": "...",
  "expected_behavior": "Application should detect overpayment." }
```

### `GET /api/datasets/{id}/tables/{table}?offset=0&limit=50`
Res `{ "table": "invoices", "total": 1480, "rows": [ {...} ] }`

### `GET /api/datasets/{id}/documents/invoices` (owner H)
Res `{ "invoice_ids": ["INV-0001", ...] }`

### `GET /api/datasets/{id}/documents/invoices/{invoice_id}.pdf` (owner H)
`application/pdf`. Returns 404 if the dataset has no `document_hints.invoice`.

### `GET /api/datasets/{id}/export.zip` (owner H)
`application/zip`: `tables/*.csv`, `tables/*.json`, `schema.json`,
`validation_report.json`, `ground_truth.json`, `documents/invoices/*.pdf` (max 20).
