# Backend Test 1: Setup + schema ingest (F0–F3)

- **Date:** 2026-09-29
- **Author:** Farhan (F), backend
- **Branch:** `F/phasef3` (or `main` after it is merged)
- **What was built so far:** the backend API skeleton (F0), the AI layer (F1),
  two ready-made templates (F2), and **this session, F3 schema ingest**: the
  backend now reads CSV files, SQLite files and Postgres databases, works out
  the tables, columns, keys, links between tables and business rules, and
  returns a schema. It never sends real data rows to the AI.

> **Tip for the tester:** paste this whole file into any AI assistant and ask
> "explain this and help me run it step by step". Every step below can be
> copied as-is.

---

## Part A: One-time setup (from zero)

You need **Windows PowerShell**, **Git** and **Python 3.12**.

### A1. Install the tools (skip what you already have)

1. Git: https://git-scm.com/download/win (default options).
2. Python **3.12** (not 3.14, some libraries have no 3.14 build yet):
   https://www.python.org/downloads/release/python-3127/, then tick
   **"Add python.exe to PATH"** during install.
3. Check it: open PowerShell and run
   ```powershell
   py -3.12 --version
   ```
   Expected: `Python 3.12.x`.

### A2. Get the code

```powershell
cd $HOME\Desktop
git clone https://github.com/M-Farhan11/DatDub.git Ai-Hackathon
cd Ai-Hackathon
git checkout F/phasef3     # or: git checkout main (after merge)
git pull
```

### A3. Create the Python environment and install the dependencies

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

- If `Activate.ps1` is blocked, run this once, then activate again:
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
- When it works, your prompt starts with `(.venv)`. **Every later PowerShell
  window needs `cd backend` + `.venv\Scripts\Activate.ps1` again.**

### A4. Create the settings file

```powershell
Copy-Item .env.example .env
```

Leave it as it is: `AI_PROVIDER=mock` means **no API keys are needed**. The
"AI" answers are canned but valid, so every test below works offline.

### A5. Start the server

```powershell
uvicorn app.main:app --reload --port 8000
```

Leave this window open (it shows the server log). Open a **second**
PowerShell window for the tests (`cd backend`, activate the venv).

### A6. Check the server is up

- Browser: http://127.0.0.1:8000/api/health → shows `{"status":"ok"}`
- Browser: http://127.0.0.1:8000/docs → the **Swagger UI**, a web page listing
  every endpoint. Click an endpoint → **Try it out** → fill in → **Execute**.
  You can do every test below either there or with the PowerShell commands.

Result: [ ] PASS [ ] FAIL  Notes: ____

### A7. Run the automated tests (sanity check)

In the second window (inside `backend`, venv active):

```powershell
python -m pytest -q --deselect tests/test_ai_live.py
```

Expected: the last line says something like `79 passed, 1 skipped` and
**0 failed**. (The skipped one needs a private Postgres; the deselected live
AI tests need real API keys.)

Result: [ ] PASS [ ] FAIL  Notes: ____

---

## Part B: Functional tests

All sample files are in `Manual Testing/samples/`. In PowerShell, first go
there (from `backend`):

```powershell
cd "..\Manual Testing\samples"
```

We use `curl.exe` (built into Windows 10/11). Type `curl.exe`, not just
`curl`. Tip: in the Swagger UI, file uploads have a **Choose File** button.

### Test 1: Templates list

- **Purpose:** the two built-in templates load.
- **Steps:** browser → http://127.0.0.1:8000/api/templates
- **Expected:** a list with `finance` (4 tables) and `ecommerce`.

Result: [ ] PASS [ ] FAIL  Notes: ____

### Test 2: Schema from a prompt (mock AI)

- **Purpose:** a text description becomes a schema.
- **Steps:**
  ```powershell
  curl.exe -s -X POST http://127.0.0.1:8000/api/schema/from-prompt -H "Content-Type: application/json" -d "{\"prompt\": \"A billing system with customers, invoices and payments\"}"
  ```
- **Expected:** JSON with `"schema"` holding `"source":"prompt"` and several
  `tables`, plus `"notes"` (with mock AI it mentions the built-in finance schema).

Result: [ ] PASS [ ] FAIL  Notes: ____

### Test 3: Schema from 4 CSV files (the main F3 test)

- **Purpose:** the backend works out tables, types, keys, links and rules from CSVs.
- **Steps:**
  ```powershell
  curl.exe -s -X POST http://127.0.0.1:8000/api/schema/from-csv -F "files=@customers.csv" -F "files=@invoices.csv" -F "files=@invoice_items.csv" -F "files=@payments.csv" -o csv_schema.json
  notepad csv_schema.json
  ```
  (Swagger: `POST /api/schema/from-csv` → **Add string item** for each file.)
- **Expected** (search in the file with Ctrl+F):
  - 4 tables: `customers`, `invoices`, `invoice_items`, `payments`.
  - `customers`: `"primary_key": "customer_id"`; `email` has
    `"semantic_type": "email"` and `"pii": true`; `phone` is `phone`, PII;
    `segment` has `allowed_values` retail / sme / corp.
  - `invoices` has a `foreign_keys` entry to `customers`.
  - `"rules"` contains `sum_of_children` (invoice total = sum of quantity × unit_price),
    `lte_parent` (payment amount ≤ invoice total) and `date_order` (issue_date before due_date).
  - `"document_hints"` → `invoice` with `header_table: "invoices"`.
  - Columns have a `"profile"` (null_rate, min/max, histogram, …).
  - **Privacy:** no real email address like `user3@mail.com` appears anywhere in the file.
  - `"notes"` explain what was linked and found.

Result: [ ] PASS [ ] FAIL  Notes: ____

### Test 4: Generate data from the CSV schema

- **Purpose:** the inferred schema is good enough to generate new data.
- **Steps:** in the Swagger UI, open `POST /api/generate` → Try it out. Replace the
  body with `{"schema": <paste the "schema" object from csv_schema.json>, "rows": {"customers": 40}}` → Execute.
  PowerShell alternative:
  ```powershell
  $s = (Get-Content csv_schema.json -Raw | ConvertFrom-Json).schema
  $body = @{ schema = $s; rows = @{ customers = 40 } } | ConvertTo-Json -Depth 20
  Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/generate -ContentType "application/json" -Body $body | Select-Object dataset_id, row_counts, @{n="overall";e={$_.report.overall}}
  ```
- **Expected:** `overall` = `PASS`; `row_counts` shows customers 40 and
  invoices 80 (the sample has exactly 2 invoices per customer).

Result: [ ] PASS [ ] FAIL  Notes: ____

### Test 5: SQLite, schema only (no rows read)

- **Purpose:** a SQLite database file is understood from its structure alone.
- **Steps:**
  ```powershell
  curl.exe -s -X POST http://127.0.0.1:8000/api/schema/from-sqlite -F "file=@shop.sqlite" -F "mode=schema_only" -F "tables=order_items"
  ```
- **Expected:** status 200; `"auto_added"` lists `orders` and `customers`
  (you asked only for `order_items`, and the parents it needs were added);
  `"rows_sampled": 0`; the note says no rows were read.

Result: [ ] PASS [ ] FAIL  Notes: ____

### Test 6: SQLite, schema + sample

- **Purpose:** with a sample, columns get statistics and child counts.
- **Steps:**
  ```powershell
  curl.exe -s -X POST http://127.0.0.1:8000/api/schema/from-sqlite -F "file=@shop.sqlite" -F "mode=schema_and_sample" -F "sample_limit=25" -o sqlite_schema.json
  notepad sqlite_schema.json
  ```
- **Expected:** `"rows_sampled": 70` (customers has only 20 rows, plus 25 + 25);
  `customers.email` is `email` + PII with **no** `top_values`; `orders` has a
  foreign key with `children_distribution`; table `audit_log` gets a generated
  key `audit_log_id` and a note about its composite primary key.

Result: [ ] PASS [ ] FAIL  Notes: ____

### Test 7: Postgres, list tables + extract (optional, needs a database)

- **Purpose:** connect to a real Postgres.
- **Only if** you have a Postgres URL (the team's Supabase demo DB arrives in F8;
  or a local Postgres, which needs `ALLOW_PRIVATE_DB_HOSTS=true` in `.env`, the default).
- **Steps:** Swagger → `POST /api/db/tables` with
  `{"connection": {"url": "postgresql://USER:PASSWORD@HOST:5432/DBNAME"}}`,
  then `POST /api/schema/from-db` with
  `{"connection": {...same...}, "tables": ["<one table>"], "mode": "schema_and_sample", "sample_limit": 200}`.
- **Expected:** step 1 lists tables with `column_count`, `estimated_rows` and
  `references`; step 2 returns a schema, `auto_added` parents, `rows_sampled` > 0.
  **The password never appears in any response.**

Result: [ ] PASS [ ] FAIL [ ] SKIPPED  Notes: ____

---

## Part C: Negative tests (bad input must give a clean error, never a crash)

Each error looks like `{"error": {"code": "...", "message": "..."}}`.
Add `-w " HTTP %{http_code}"` to see the status code.

| # | Steps | Expected |
|---|---|---|
| N1 | `curl.exe -s -w " HTTP %{http_code}" -X POST http://127.0.0.1:8000/api/schema/from-csv -F "files=@empty.csv"` | 400, code `invalid_csv` |
| N2 | `curl.exe -s -w " HTTP %{http_code}" -X POST http://127.0.0.1:8000/api/schema/from-sqlite -F "file=@fake.sqlite"` | 400, code `invalid_sqlite_file` |
| N3 | `curl.exe -s -w " HTTP %{http_code}" -X POST http://127.0.0.1:8000/api/schema/from-sqlite -F "file=@shop.sqlite" -F "tables=ghosts"` | 404, code `table_not_found` |
| N4 | Swagger `POST /api/db/tables` with `{"connection": {"url": "mysql://u:p@example.com/db"}}` | 422, code `db_unsupported_dialect` |
| N5 | Swagger `POST /api/db/tables` with `{"connection": {"url": "postgresql://u:p@example.com/db?host=127.0.0.1"}}` | 422, `db_unsupported_dialect` (sneaky host override blocked) |
| N6 | Swagger `POST /api/db/tables` with `{"connection": {"url": "postgresql://reader:MySecret123@no-such-host.invalid/db"}}` | 400, `db_unreachable`; the text `MySecret123` is **not** in the response or the server window |
| N7 | Swagger `POST /api/schema/from-db` with `{"connection": {"password": "MySecret123"}, "tables": []}` | 422, `validation_error`; `MySecret123` not in the response |

Result N1–N7: [ ] PASS [ ] FAIL  Notes: ____

### N8: Private and cloud-metadata hosts are blocked (the "deployed" setting)

- **Purpose:** the hosted app must not be tricked into connecting to internal machines.
- **Steps:**
  1. Stop the server (Ctrl+C). In `.env` set `ALLOW_PRIVATE_DB_HOSTS=false`. Start the server again (A5).
  2. Swagger `POST /api/db/tables` with each of these URLs:
     - `postgresql://reader:MySecret123@127.0.0.1:5432/postgres`
     - `postgresql://reader:MySecret123@169.254.169.254:5432/postgres`
     - `postgresql://reader:MySecret123@localhost:5432/postgres`
  3. **Set `ALLOW_PRIVATE_DB_HOSTS=true` again afterwards** and restart.
- **Expected:** every call → 400, code `db_host_not_allowed`; `MySecret123`
  appears neither in the response nor in the server window.

Result: [ ] PASS [ ] FAIL  Notes: ____

---

## Known limitations (not bugs yet)

- **Scenarios** are proposed but not yet injected into generated data (F7).
- **Invoice PDF** and **ZIP export** return `501 not_implemented` (Haider, H6/H7).
- The generator is a first cut: it does not yet use the sampled profiles
  (distributions/histograms) or null/outlier rates (F5); generated values are
  simple placeholders.
- No Supabase demo database yet (F8), so Test 7 needs your own Postgres.
- There is no frontend yet. Everything is tested through the API.
- A table that references itself (e.g. `employees.manager_id`) loses that link, with a note.
- With `AI_PROVIDER=mock`, the AI answers are canned. Real AI needs keys in `.env` (ask Farhan; never commit them).
