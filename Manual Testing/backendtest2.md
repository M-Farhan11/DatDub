# Backend Test 2: Generation engine (F5)

- **Date:** 2026-09-29
- **Author:** Farhan (F), backend
- **Branch:** `F/phasef5` (or `main` after it is merged)
- **What this session built:** the **generation engine**. From a schema it
  now produces realistic synthetic tables: realistic names/emails/addresses
  (Faker pools), numbers and categories that follow the sample's shape,
  child rows per parent (e.g. invoices per customer), business rules
  enforced (invoice total = sum of its items, dates in order, payment ≤
  invoice), optional empty values (null rate) and odd values (outlier rate),
  and a per-table row cap. The same seed always gives the same data.

> **Tip for the tester:** paste this whole file into any AI assistant and ask
> "explain this and help me run it step by step".

---

## Setup

Do **Part A of `backendtest1.md`** first (Python, venv, `.env`, server
running on port 8000). Nothing new to install: no new env vars, no new
dependencies.

Open a **second** PowerShell window for the tests:

```powershell
cd backend
.venv\Scripts\Activate.ps1
```

Every test below starts from the finance template. Run this once in that
window (re-run it if you open a new window):

```powershell
$api = "http://127.0.0.1:8000/api"
$schema = Invoke-RestMethod "$api/templates/finance"
function Gen($rows, $seed = 42, $nullRate = 0, $outlierRate = 0) {
  $body = @{ schema = $schema; rows = @{ customers = $rows }; seed = $seed;
             null_rate = $nullRate; outlier_rate = $outlierRate } | ConvertTo-Json -Depth 20
  Invoke-RestMethod -Method Post -Uri "$api/generate" -ContentType "application/json" -Body $body
}
```

**Swagger alternative:** http://127.0.0.1:8000/docs → `GET /api/templates/{template_id}`
(id `finance`) → copy the response → `POST /api/generate` → body
`{"schema": <paste>, "rows": {"customers": 5000}, "seed": 42}`.

---

## Tests

### T1. Generate 5,000 customers quickly

*Purpose:* the engine produces all four tables in under 5 seconds.

```powershell
Measure-Command { $r = Gen 5000 } | Select-Object TotalSeconds
$r = Gen 5000
$r.row_counts
```

*Expected:* `TotalSeconds` below 5. `row_counts` shows `customers 5000`,
`invoices` about 22,000 (1–8 per customer), `invoice_items` about 3–4 per
invoice, `payments` about 1 per invoice. A `dataset_id` starting with `ds_`.

Result: [ ] PASS [ ] FAIL  Notes: ____

### T2. Data looks realistic

*Purpose:* names, emails and addresses are varied and realistic, not a dozen repeats.

```powershell
$r.previews.customers | Select-Object -First 10 | Format-Table customer_id, full_name, email, city, country, created_at
```

*Expected:* IDs like `CUS-00001`; real-looking, varied full names; emails like
`jane.smith12@example.com` (always `example.com/.org/.net`); dates as
`YYYY-MM-DD`.

Result: [ ] PASS [ ] FAIL  Notes: ____

### T3. Same seed → identical data; different seed → different data

```powershell
$a = Gen 200 7; $b = Gen 200 7; $c = Gen 200 8
($a.previews.customers | ConvertTo-Json) -eq ($b.previews.customers | ConvertTo-Json)
($a.previews.customers | ConvertTo-Json) -eq ($c.previews.customers | ConvertTo-Json)
```

*Expected:* first line `True`, second line `False`.

Result: [ ] PASS [ ] FAIL  Notes: ____

### T4. Business rules hold

*Purpose:* totals, dates and payments follow the rules. Runs a short check
script against the engine directly (venv must be active, inside `backend`).

```powershell
python -c "from app.templates import finance; from app.engine.generator import generate; t = generate(finance.build(), {'customers': 2000}, seed=1); i, it, p = t['invoices'], t['invoice_items'], t['payments']; s = (it.quantity * it.unit_price).groupby(it.invoice_id).sum().round(2); tot = i.set_index('invoice_id').total; print('totals match:', bool(((tot.loc[s.index] - s).abs() <= 0.01).all())); print('due >= issue:', bool((i.due_date >= i.issue_date).all())); print('payment <= invoice:', bool((p.amount <= p.invoice_id.map(tot)).all()))"
```

*Expected:*
```
totals match: True
due >= issue: True
payment <= invoice: True
```

Result: [ ] PASS [ ] FAIL  Notes: ____

### T5. Null rate adds empty values only where allowed

```powershell
$r = Gen 1000 42 0.3
$r.previews.customers | Select-Object -First 20 | Format-Table customer_id, email, phone, company
```

*Expected:* some `phone` and `company` cells are empty (these columns allow
empty values). `customer_id` and `email` are **never** empty.

Result: [ ] PASS [ ] FAIL  Notes: ____

### T6. Paging through a full table

```powershell
$r = Gen 500
$page = Invoke-RestMethod "$api/datasets/$($r.dataset_id)/tables/invoices?offset=100&limit=5"
$page.total; $page.rows | Format-Table invoice_id, customer_id, issue_date, total
```

*Expected:* `total` equals `$r.row_counts.invoices`; 5 rows starting at
`INV-00101`.

Swagger: `GET /api/datasets/{dataset_id}/tables/{table}`.

Result: [ ] PASS [ ] FAIL  Notes: ____

### T7. Big job: 100,000 customers with child tables capped

*Purpose:* a large request finishes in time and child tables never exceed the
per-table cap (default 100,000).

```powershell
Measure-Command { $r = Gen 100000 } | Select-Object TotalSeconds
$r.row_counts
```

*Expected:* under 30 seconds. `customers 100000`; every other table is
**at most 100000** (they would be larger, so the engine scaled them down).

Result: [ ] PASS [ ] FAIL  Notes: ____

---

## Negative tests

### N1. Too many rows → clean 422

```powershell
try { Gen 10000000 } catch { $_.ErrorDetails.Message }
```

*Expected:* `{"error":{"code":"rows_limit_exceeded","message":"Max 100,000 rows per table. ..."}}`

Result: [ ] PASS [ ] FAIL  Notes: ____

### N2. Null rate out of range → 422

```powershell
try { Gen 100 42 0.9 } catch { $_.ErrorDetails.Message }
```

*Expected:* a 422 validation error mentioning `null_rate` (max 0.5).

Result: [ ] PASS [ ] FAIL  Notes: ____

### N3. Unknown dataset / table → 404

```powershell
try { Invoke-RestMethod "$api/datasets/ds_doesnotexist/tables/invoices" } catch { $_.ErrorDetails.Message }
$r = Gen 50
try { Invoke-RestMethod "$api/datasets/$($r.dataset_id)/tables/nope" } catch { $_.ErrorDetails.Message }
```

*Expected:* first `dataset_not_found`, second `table_not_found`.

Result: [ ] PASS [ ] FAIL  Notes: ____

---

## Known limitations (not bugs)

- The response does not yet tell you **when** a child table was capped (T7);
  a `notes` field is pending agreement with the frontend.
- The validation report still only checks keys (PK/FK). Rule checks, the
  "expected" scenario violations and similarity % come in F6.
- Edge-case scenarios (`scenarios` in the request) are accepted but not
  injected yet (F7); ground truth stays empty.
- Payment dates can be long after the invoice date (valid, just not always
  realistic).
- Datasets live in memory: they disappear after 60 minutes or a server restart.
