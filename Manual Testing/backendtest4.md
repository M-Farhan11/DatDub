# Backend Test 4: Edge-case scenarios (F7), database rules (F8) and hardening

- **Date:** 2026-09-29
- **Author:** Farhan (F), backend
- **Branch:** `F/phasef7` (or `main` after it is merged)
- **What this session built:**
  1. **Scenario Studio backend:** the chosen edge cases (missing values, extreme
     values, duplicates, boundary dates, rule breaks) are now really injected into
     the generated data, listed in the **ground truth**, and shown in the report as
     **expected**, never as failures.
  2. **Database rules:** importing a database with "Schema + sample" now also finds
     its business rules (e.g. "invoice total = sum of its items").
  3. **Hardening:** bad requests get a clean `422` error instead of wrong data or a crash.

> **Tip for the tester:** paste this whole file into any AI assistant and ask
> "explain this and help me run it step by step".

---

## Setup

Do **Part A of `backendtest1.md`** first (Python, venv, `.env`, server running on
port 8000). Nothing new to install. New **optional** `.env` settings (defaults are fine):

| Setting | Default | Meaning |
|---|---|---|
| `MAX_TOTAL_CELLS` | `8000000` | max rows × columns in one generation |
| `MAX_STORE_CELLS` | `30000000` | memory budget for all kept datasets |
| `MAX_CONCURRENT_GENERATIONS` | `2` | generations running at the same time |

New sample file: `Manual Testing/samples/finance_demo.sqlite`.

Open a **second** PowerShell window:

```powershell
cd backend
.venv\Scripts\Activate.ps1
$api = "http://127.0.0.1:8000/api"
$schema = Invoke-RestMethod "$api/templates/finance"
function Try-Gen($b) {
  try { $r = Invoke-RestMethod -Method Post -Uri "$api/generate" -ContentType "application/json" -Body ($b | ConvertTo-Json -Depth 20); "200 OK"; return $r }
  catch { "$($_.Exception.Response.StatusCode.value__) " + $_.ErrorDetails.Message }
}
```

**Swagger alternative for every test:** http://127.0.0.1:8000/docs

---

## Tests

### 1. The AI proposes edge cases

*Purpose:* the scenario endpoint returns one proposal per scenario kind.

*Steps:*
```powershell
$prop = Invoke-RestMethod -Method Post -Uri "$api/scenarios/propose" -ContentType "application/json" `
  -Body (@{ schema = $schema; instruction = "Add realistic edge cases for testing" } | ConvertTo-Json -Depth 20)
$prop.proposals | Format-Table id, kind, table, column, rule_id, suggested_count -AutoSize
```
Swagger: `POST /api/scenarios/propose`, body `{"schema": <finance template>, "instruction": "Add realistic edge cases for testing"}`.

*Expected (with `AI_PROVIDER=mock`):* 5 proposals `s1`–`s5`, kinds `rule_violation`
(payments, rule `r3`), `null_burst` (customers.phone), `extreme_value` (invoices.total),
`boundary_date` (customers.created_at), `duplicate_record` (payments). With a real AI
provider the proposals differ, but every one uses one of these 5 kinds.

Result: [ ] PASS [ ] FAIL  Notes: ____

### 2. Generate with all proposed scenarios

*Purpose:* the scenarios are injected, listed in the ground truth, and the report still passes.

*Steps (continue from test 1):*
```powershell
$sel = @($prop.proposals | ForEach-Object { @{ proposal = $_; count = $_.suggested_count } })
$r = Try-Gen @{ schema = $schema; rows = @{ customers = 1000 }; seed = 42; scenarios = $sel }
$r = $r[1]
"overall: " + $r.report.overall
$r.ground_truth | Format-Table scenario_id, kind, table, @{n='rows';e={$_.affected_ids.Count}} -AutoSize
$r.report.checks | Where-Object { $_.expected_violations -gt 0 } | Format-Table table, name, detail -AutoSize
```

*Expected:*
- `overall: PASS`
- ground truth has 5 lines: s1 = 5 rows, s2 = 10, s3 = 3, s4 = 5, s5 = 4
- the checks with expected violations include:
  - `payments` · `Rule r3: A payment never exceeds its invoice total` · `…, 5 injected (expected)`
  - `invoices` · `Rule r1: Invoice total equals the sum of its line items` · `…, 3 injected (expected)`
  - `invoices` · `Rule r5: An invoice is issued on or after the customer was created` · `…, 5 injected (expected)`
    (the boundary dates on customers make some of their invoices "too early"; this knock-on effect is expected too)

Result: [ ] PASS [ ] FAIL  Notes: ____

### 3. Exactly the chosen records (acceptance test)

*Purpose:* 3 hand-picked scenarios give exactly those records.

*Steps:*
```powershell
$three = @(
  @{ proposal = @{ id = "s1"; kind = "rule_violation"; table = "payments"; rule_id = "r3"; title = "Overpaid" }; count = 4 },
  @{ proposal = @{ id = "s2"; kind = "null_burst"; table = "customers"; column = "email"; title = "No email" }; count = 6 },
  @{ proposal = @{ id = "s3"; kind = "duplicate_record"; table = "payments"; title = "Paid twice" }; count = 3 }
)
$r = (Try-Gen @{ schema = $schema; rows = @{ customers = 300 }; seed = 11; scenarios = $three })[1]
$r.report.overall
$r.ground_truth | Format-Table scenario_id, @{n='rows';e={$_.affected_ids.Count}}, @{n='ids';e={$_.affected_ids -join ', '}} -AutoSize
```

*Expected:* `PASS`; s1 = 4 ids, s2 = 6 ids, s3 = 3 ids; the s3 ids are **new** payment ids
(higher numbers than the others, e.g. `PAY-00…`). In the report, `customers` ·
`Types & nullability` shows `6 injected (expected)` (email is required, so the missing
emails are the intended test).

Result: [ ] PASS [ ] FAIL  Notes: ____

### 4. Same seed, same edge cases

*Purpose:* injection is reproducible.

*Steps:* run test 3 twice and compare:
```powershell
$a = (Try-Gen @{ schema = $schema; rows = @{ customers = 300 }; seed = 11; scenarios = $three })[1]
$b = (Try-Gen @{ schema = $schema; rows = @{ customers = 300 }; seed = 11; scenarios = $three })[1]
($a.ground_truth | ConvertTo-Json -Depth 5) -eq ($b.ground_truth | ConvertTo-Json -Depth 5)
```

*Expected:* `True`

Result: [ ] PASS [ ] FAIL  Notes: ____

### 5. A database's business rules are found

*Purpose:* "Schema + sample" import finds the rules inside the database.

*Steps (Swagger):* `POST /api/schema/from-sqlite` → **Try it out** → `file` = `Manual Testing/samples/finance_demo.sqlite`,
`mode` = `schema_and_sample` → Execute.

*Expected:* `200`. `schema.rules` has **7** rules, among them:
- `sum_of_children` · `invoices.total equals the sum of invoice_items quantity * unit_price`
- `lte_parent` · `payments.amount is at most invoices.total`
- `date_order` · `invoices.issue_date is on or before due_date`
- `allowed_values` on `invoices.status`

`notes` contains `Found 7 rule(s) that hold for every row in the database (checked with aggregate queries).`
In `customers`, the `email` column has `"unique": true`.

Then copy the whole `schema` object into `POST /api/generate` with
`"rows": {"customers": 500}` → **Expected:** `report.overall` = `PASS`, and every
`Rule …` check shows `…/… pass` with no failures.

Result: [ ] PASS [ ] FAIL  Notes: ____

### 6. Schema-only import reads no rows and makes up no rules

*Steps:* same as test 5 with `mode` = `schema_only`.

*Expected:* `200`; `schema.rules` is `[]`; `notes` says "Schema only: … (no rows were read)".

Result: [ ] PASS [ ] FAIL  Notes: ____

### 7. (Optional, needs a Postgres you can write to) The Supabase demo seed

*Purpose:* the demo database script works and its rules are detected.

*Steps:*
1. Create an **empty scratch database** (pgAdmin → Databases → Create, e.g. `demo_seed`).
   The script drops and recreates tables named `customers`, `invoices`, `invoice_items`, `payments`.
2. Open `scripts/seed_demo_db.sql` in pgAdmin's Query Tool on that database and run it.
3. Run the 3 "Sanity check" queries at the bottom of the script (remove the `--`).
4. Swagger `POST /api/schema/from-db`, body:
   `{"connection": {"url": "postgresql://USER:PASSWORD@localhost:5432/demo_seed"}, "tables": ["payments", "invoice_items"], "mode": "schema_and_sample"}`
   (needs `ALLOW_PRIVATE_DB_HOSTS=true` in `.env` for `localhost`).

*Expected:* step 2 finishes without errors; each sanity query returns `0`; step 4 returns
`200` with `auto_added` = `invoices`, `customers` and rules that include `sum_of_children`
on `invoices.total` and `lte_parent` on `payments.amount`. The password is **not** anywhere in the response.

Developer shortcut: `$env:TEST_PG_SEED_URL = "postgresql://USER:PASSWORD@localhost:5432/demo_seed"; pytest tests/test_db_rules.py -k postgres -v`

Result: [ ] PASS [ ] FAIL  Notes: ____

---

## Negative tests

Each must return the error shown, and **no** dataset is created.

| # | Steps | Expected |
|---|---|---|
| N1 | `Try-Gen @{ schema = $schema; rows = @{ customers = 100 }; seed = -1 }` | `422 invalid_schema`: "seed must be between 0 and 4294967295." |
| N2 | `Try-Gen @{ schema = $schema; rows = @{ invoices = 100 } }` | `422 invalid_schema`: "rows: 'invoices' is a child table; its row count follows its parent." |
| N3 | `Try-Gen @{ schema = $schema; rows = @{ customers = 100 }; locale = "xx_XX" }` | `422 invalid_schema`: "Unknown locale 'xx_XX'…" |
| N4 | `Try-Gen @{ schema = $schema; rows = @{ customers = 100 }; scenarios = @(@{ proposal = @{ id = "s1"; kind = "null_burst"; table = "customers"; column = "customer_id"; title = "bad" }; count = 5 }) }` | `422 invalid_schema`: "Scenario s1 (null_burst): cannot target a key column." |
| N5 | `Try-Gen @{ schema = $schema; rows = @{ customers = 100000000 } }` | `422 rows_limit_exceeded`: "Max 100,000 rows per table…" |
| N6 | A unique column with only 2 possible values, 10 rows:<br>`$u = @{ name="t"; source="template"; tables=@(@{ name="things"; primary_key="id"; columns=@(@{name="id";data_type="string";semantic_type="id";unique=$true}, @{name="code";data_type="integer";semantic_type="generic_number";unique=$true;min=0;max=1}) }) }`<br>`Try-Gen @{ schema = $u; rows = @{ things = 10 } }` | `422 invalid_schema`: "Column 'code' is unique but its range has only 2 distinct values for 10 rows…" |
| N7 | Swagger `POST /api/generate` with `"rows": {"customers": 0}` | `422 invalid_schema`: "rows: 'customers' needs at least 1 row." |
| N8 | Swagger `POST /api/generate` with `"schema": {"name": "e", "source": "template", "tables": []}` | `422 invalid_schema`: "The schema has no tables." |

Result: N1 [ ] N2 [ ] N3 [ ] N4 [ ] N5 [ ] N6 [ ] N7 [ ] N8 [ ]  Notes: ____

---

## Known limitations (not bugs)

- The Supabase demo project itself is not set up yet (needs the team's Supabase account).
- Rules are only detected in **Schema + sample** mode; schema-only reads no data at all.
- A `range` rule on a column that another rule computes (e.g. a max on an invoice total)
  can conflict; the report then shows it honestly as FAIL.
- The generator's "table capped at N rows" note is not in the API response yet
  (proposed to Haider as `GenerateResponse.notes`).
- Duplicated records are **extra** rows, so `row_counts` grow by the duplicate count.
- No frontend yet: test through PowerShell or Swagger.
