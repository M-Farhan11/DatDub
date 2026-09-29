# Frontend Test 3: ZIP export (H7)

- **Date:** 2026-09-30
- **Author:** Haider (H)
- **Branch:** `frontend-v1` → pushed to `frontend` (not merged into `main` yet at the time of writing)
- **What was built:** the **Download ZIP** button now downloads the whole dataset in
  one file: every table as CSV and JSON, the schema, the quality report, the answer
  key of edge cases (ground truth), the first 20 invoice PDFs and a short README.

> **Tip for the tester:** paste this file into any AI assistant and ask
> "explain this and help me run it step by step".

## Setup

Follow Part A of `Manual Testing/frontendtest1.md`. Nothing new to install.
If the backend was already running, **restart it** so it picks up the new code.

---

## Tests

### Test 1: Download the ZIP from the studio
- **Purpose:** the main export works.
- **Steps:** http://localhost:5173 → **Try an example** → **Continue** →
  **Suggest** → tick 2 edge cases → **Generate data** → **Continue to export** →
  **Download ZIP**.
- **Expected:** the button shows "Preparing the ZIP…" for a moment, then
  `finance_demo.zip` downloads. No "coming soon" message.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 2: What is inside
- **Purpose:** the ZIP has every promised file.
- **Steps:** right-click the ZIP → **Extract All** → open the folder.
- **Expected:**
  - `tables\` with `customers.csv`, `customers.json`, `invoices.csv`, `invoices.json`,
    `invoice_items.csv`, `invoice_items.json`, `payments.csv`, `payments.json`
  - `schema.json`, `validation_report.json`, `ground_truth.json`, `README.txt`
  - `documents\invoices\` with 20 PDFs (`INV-00001.pdf` … `INV-00020.pdf`)
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 3: Row counts match the studio
- **Purpose:** the files hold all the rows, not only the preview.
- **Steps:** open `tables\customers.csv` in Excel. Compare the number of data rows
  (last row number minus 1 for the header) with the Data tab in the studio.
- **Expected:** the same count, e.g. 200 customers for the template default, or the
  number you chose in Configure. Dates look like `2024-03-21`.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 4: Answer key matches the Edge cases tab
- **Purpose:** the ground truth file is the same answer key as in the studio.
- **Steps:** open `ground_truth.json` in Notepad. Compare the IDs with the
  **Edge cases** tab of the Results page.
- **Expected:** one entry per edge case you ticked, with the same affected IDs.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 5: Invoice PDFs open
- **Purpose:** the PDFs in the ZIP are real invoices.
- **Steps:** open `documents\invoices\INV-00001.pdf`.
- **Expected:** the same invoice as in the studio's Invoices tab, with a Total that
  equals the sum of its items.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 6: Large dataset
- **Purpose:** big exports still work.
- **Steps:** Start a new dataset → Try the finance example → Configure: type `20000`
  in Rows in customers → Generate → Export → Download ZIP.
- **Expected:** the download finishes within a few seconds (about 11 MB).
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

## Negative tests

### Test 7: Template without invoices
- **Steps:** generate the **E-commerce** template and download its ZIP.
- **Expected:** the ZIP has the tables and JSON files but **no** `documents` folder.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 8: Expired dataset
- **Steps:** generate a dataset, restart the backend (Ctrl+C, start again), then click
  **Download ZIP** on the Export page.
- **Expected:** "This dataset has expired. Generate it again." with a button back to Configure.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 9: Unknown dataset in Swagger
- **Steps:** http://127.0.0.1:8000/docs → `GET /api/datasets/{dataset_id}/export.zip`
  with `ds_missing` → Execute.
- **Expected:** 404 with `"code": "dataset_not_found"`.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

## Known limitations (not bugs)

- Only the first 20 invoices are included as PDFs; every invoice can still be opened
  one by one in the Invoices tab.
- In sample-data mode (`VITE_USE_FIXTURES=true`) the ZIP button still says "coming soon".
- Datasets are deleted after 60 minutes; download the ZIP before then.
