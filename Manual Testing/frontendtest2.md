# Frontend Test 2: Invoice PDFs (H6)

- **Date:** 2026-09-30
- **Author:** Haider (H)
- **Branch:** `frontend-v1` → pushed to `frontend` (not merged into `main` yet at the time of writing)
- **What was built:** DatDub now creates a synthetic **invoice PDF** for every invoice
  in a generated dataset. The PDF uses the generated data only: customer, dates,
  status, line items, total, amount paid and balance due. The total on the PDF
  always equals the sum of its line items, unless you added an edge case that
  breaks that rule on purpose.

> **Tip for the tester:** paste this file into any AI assistant and ask
> "explain this and help me run it step by step".

## Setup

Follow Part A of `Manual Testing/frontendtest1.md` (Node, backend, frontend, both
servers running, `VITE_USE_FIXTURES=false`). Nothing new to install.
If the backend was already running, **restart it** (Ctrl+C, then run the uvicorn
command again) so it picks up the new code.

---

## Tests

### Test 1: Invoice preview in the studio
- **Purpose:** invoices show as real PDFs.
- **Steps:** http://localhost:5173 → **Try an example** → **Continue** →
  **Medium 5,000** → **Generate data** → open the **Invoices** tab → click `INV-00001`,
  then `INV-00002`.
- **Expected:** a PDF appears on the right (not "coming soon"): "INVOICE #INV-00001",
  Billed to (name, address, email), From "DatDub Test Supplier Ltd.", issue date, due
  date, status, a table Item / Qty / Price / Amount, a green "Total", Amount paid,
  Balance due, and the footer "Synthetic document … Not a real invoice."
  Clicking another ID shows that invoice.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 2: The total adds up
- **Purpose:** the invoice reconciles with its items.
- **Steps:** on one invoice, add up the **Amount** column with a calculator.
  Then open the **Data** tab → `invoices` and find the same invoice ID.
- **Expected:** the sum of the amounts equals the **Total** on the PDF, and equals
  the `total` value in the Data tab (to the cent).
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 3: Download / open the PDF directly
- **Purpose:** the PDF works outside the studio.
- **Steps:** Swagger UI at http://127.0.0.1:8000/docs → `GET /api/datasets/{dataset_id}/documents/invoices/{invoice_id}.pdf`.
  First run `POST /api/generate` in Swagger (schema from `GET /api/templates/finance`,
  `"rows": {"customers": 20}`) and copy the `dataset_id` from its response. Use that ID
  and `INV-00001`. Click **Execute**, then **Download file**.
- **Expected:** status 200, `content-type: application/pdf`; the file opens in any PDF viewer.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 4: Edge case visible on the invoice
- **Purpose:** an injected mismatch is visible, so tests can catch it.
- **Steps:** in Swagger, `POST /api/generate` with the finance template schema
  (copy it from `GET /api/templates/finance`), `"rows": {"customers": 20}` and this scenario:
  ```json
  "scenarios": [{"count": 2, "proposal": {"id": "t1", "kind": "rule_violation", "table": "invoices",
    "column": "total", "rule_id": "r1", "title": "Total does not match items", "suggested_count": 2,
    "description": "Totals that differ from the items.", "expected_behavior": "Reconciliation flags it."}}]
  ```
  Take one ID from `ground_truth[0].affected_ids` and open its PDF as in Test 3.
- **Expected:** the PDF shows a **Subtotal** (the sum of the items) and a different
  **Total**. Normal invoices show only the Total.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

## Negative tests

### Test 5: Unknown invoice
- **Steps:** Swagger → the PDF endpoint with a valid dataset ID and invoice `INV-99999`.
- **Expected:** 404 with `"code": "invoice_not_found"`.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 6: Template without invoices
- **Steps:** generate the **E-commerce** template, then call the PDF endpoint with any ID.
  In the studio, the Results page has no **Invoices** tab for this template.
- **Expected:** 404 with `"code": "no_documents"`; no Invoices tab in the studio.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 7: Expired dataset
- **Steps:** restart the backend (Ctrl+C, run again), then in the studio click another
  invoice in the Invoices tab of the dataset you generated before the restart.
- **Expected:** "This dataset has expired. Generate it again." with a button back to Configure.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

## Known limitations (not bugs)

- The supplier ("From") is always "DatDub Test Supplier Ltd.": schemas have no seller table.
- Tax is shown only when the invoice table has a tax/VAT column (the finance template has none).
- The ZIP download still shows "coming soon" (task H7).
- In sample-data mode (`VITE_USE_FIXTURES=true`) the invoice preview still says "coming soon".
