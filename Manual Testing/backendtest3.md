# Backend Test 3: Validation report (F6)

- **Date:** 2026-09-29
- **Author:** Farhan (F), backend
- **Branch:** `F/phasef6` (or `main` after it is merged)
- **What this session built:** the **quality report** returned by every
  generation. Besides the key checks it now checks column types and empty
  values, checks **every business rule** row by row (pass/fail counts), counts
  deliberately injected edge cases as **expected** (not failures), and gives a
  **similarity %** that compares the synthetic data with the uploaded sample.

> **Tip for the tester:** paste this whole file into any AI assistant and ask
> "explain this and help me run it step by step".

---

## Setup

Do **Part A of `backendtest1.md`** first (Python, venv, `.env`, server
running on port 8000). Nothing new: no new env vars, no new dependencies.

Open a **second** PowerShell window:

```powershell
cd backend
.venv\Scripts\Activate.ps1
$api = "http://127.0.0.1:8000/api"
$schema = Invoke-RestMethod "$api/templates/finance"
function Gen($s, $rows, $nullRate = 0, $outlierRate = 0) {
  $body = @{ schema = $s; rows = @{ customers = $rows }; seed = 42;
             null_rate = $nullRate; outlier_rate = $outlierRate } | ConvertTo-Json -Depth 20
  Invoke-RestMethod -Method Post -Uri "$api/generate" -ContentType "application/json" -Body $body
}
```

**Swagger alternative:** http://127.0.0.1:8000/docs → `GET /api/templates/{template_id}`
(id `finance`) → copy the response → `POST /api/generate` → body
`{"schema": <paste>, "rows": {"customers": 5000}, "seed": 42}` → look at `report`.

---

## Tests

### T1. Clean generation: every check passes

*Purpose:* a normal generation reports all checks as PASS.

```powershell
$r = Gen $schema 5000
$r.report.overall
$r.report.checks | Format-Table status, table, name, detail -AutoSize
```

*Expected:*
- `overall` = `PASS`.
- **18 checks**, all `PASS`:
  - for each of `customers`, `invoices`, `invoice_items`, `payments`:
    `PK uniqueness` (detail like `5000/5000 unique`) and `Types & nullability`
    (`… rows valid`);
  - `FK integrity (customer_id → customers)` on invoices and
    `FK integrity (invoice_id → invoices)` on invoice_items and payments;
  - 7 rule checks `Rule r1: …` to `Rule r7: …` (e.g. `Rule r1: Invoice total
    equals the sum of its line items`, detail `N/N pass`).
- Every `score` is `1`; every `expected_violations` is `0`.

Result: [ ] PASS [ ] FAIL  Notes: ____

### T2. Noise does not break the report

*Purpose:* empty values (null rate) and odd numbers (outlier rate) only go
where allowed, so the report stays green.

```powershell
$r = Gen $schema 5000 0.1 0.05
$r.report.overall
($r.report.checks | Where-Object status -ne "PASS").Count
```

*Expected:* `PASS` and `0`.

Result: [ ] PASS [ ] FAIL  Notes: ____

### T3. Template has no similarity score

*Purpose:* similarity needs a real sample; templates have none.

```powershell
$r.report.similarity -eq $null
```

*Expected:* `True`.

Result: [ ] PASS [ ] FAIL  Notes: ____

### T4. CSV sample → similarity %

*Purpose:* when the schema comes from an uploaded sample, the report says how
close the synthetic data is to it.

```powershell
cd "..\Manual Testing\samples"
curl.exe -s -X POST "$api/schema/from-csv" -F "files=@customers.csv" -F "files=@invoices.csv" -F "files=@invoice_items.csv" -F "files=@payments.csv" -o csv_schema.json
$csv = (Get-Content csv_schema.json -Raw | ConvertFrom-Json).schema
$r = Gen $csv 1000
$r.report.overall
$r.report.similarity.overall
$r.report.similarity.per_column
cd ..\..\backend
```

*Expected:*
- `overall` = `PASS`, 16 checks (5 rules inferred from the CSV).
- `similarity.overall` about **0.74** (74%).
- `per_column` lists 6 columns. Category and item columns are high
  (`customers.segment`, `invoices.status`, `invoice_items.quantity`,
  `invoice_items.unit_price` ≈ 0.97–0.98). `invoices.total` (≈ 0.36) and
  `payments.amount` (≈ 0.15) are low. That is expected: those two are
  **computed by rules** (sum of items, payment ≤ invoice), not copied from the
  sample, and the sample file pays exactly half of every invoice.
- No ID column (`customer_id`, `invoice_id`, …) appears in `per_column`.

Result: [ ] PASS [ ] FAIL  Notes: ____

### T5. Broken data is caught (automated)

*Purpose:* prove that bad rows show up as FAIL and injected rows as
"expected". The engine never produces bad rows on purpose, so this is tested
with a script that breaks rows by hand.

```powershell
python -m pytest tests/test_validation.py -v
```

*Expected:* `10 passed`. The important ones:
- `test_each_broken_row_fails_its_check`: duplicate ID, orphan link, empty
  required name, text in a number column and one broken row per rule each turn
  their check into `FAIL`, with counts like `4271/4272 pass`.
- `test_injected_violations_are_expected_not_failures`: 3 bad payments listed
  in the ground truth give `PASS` with `3 injected (expected)`; one more bad
  payment that is **not** listed gives `FAIL`.
- `test_report_speed_100k`: the report on 100,000 customers takes under 5 s.

Result: [ ] PASS [ ] FAIL  Notes: ____

### T6. Full backend suite still green

```powershell
python -m pytest -q
```

*Expected:* `127 passed, 3 skipped` (the 3 skipped need real API keys or a
Postgres URL).

Result: [ ] PASS [ ] FAIL  Notes: ____

---

## Negative tests

| # | Steps | Expected |
|---|---|---|
| N1 | Swagger `POST /api/generate` with body `{"rows": {"customers": 10}}` (no schema) | 422, code `validation_error` |
| N2 | Swagger `POST /api/generate` with the finance schema and `"rows": {"customers": 10000000}` | 422, code `rows_limit_exceeded` (no report is built) |

Result N1–N2: [ ] PASS [ ] FAIL  Notes: ____

---

## Known limitations (not bugs)

- Edge-case scenarios are not injected yet (F7), so through the API every
  `expected_violations` is `0` and ground truth is empty. The "expected"
  logic is covered by T5 only.
- Similarity is only shown for CSV uploads and database "schema + sample"
  mode; templates and prompts have no sample, so it is `null`.
- Rule-computed columns (totals, payment amounts) can score low on
  similarity even though they are correct (see T4).
- The response still does not say when a child table was capped (pending
  `notes` field, see backendtest2 T7).
