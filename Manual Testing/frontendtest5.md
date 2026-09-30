# Frontend Test 5: Results page with full-width tables + Documents button

- **Date:** 2026-09-30
- **Author:** H area, made in Farhan's session with Haider's agreement
- **Branch:** `F/phasef9`
- **What was built:** on Results, the Data tab now shows the table names side by side in one wide
  card (the selected one filled blue) with a full-width, taller table below. The Invoices tab uses
  the same wide card for invoice numbers (with search) and shows the PDF full width. The sidebar
  **Documents** button is hidden when the schema has no invoices, instead of sitting there
  greyed out and doing nothing.

## Setup

Same as `Manual Testing/frontendtest4.md` (nothing new to install). Start the backend with the venv:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Then in `frontend/` run `npm run dev` and open http://localhost:5173.

---

## Tests

### Test 1: Table strip + full-width table
- **Purpose:** wide tables have room.
- **Steps:** **Launch studio** → **Load finance example** → **Continue** → **Generate data** → **Data** tab.
- **Expected:** one wide white card holds `customers`, `invoices`, `invoice_items`, `payments` side by
  side, each with its row count. The selected one is solid blue with white text. Below it, the table uses
  the full page width (there is no list of tables on the left any more).
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 2: Switch tables and pages
- **Purpose:** the strip drives the table.
- **Steps:** click `invoice_items`, then **Next** under the table.
- **Expected:** `invoice_items` turns blue and its columns show. Next loads rows 51–100.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 3: Invoices strip + full-width PDF
- **Purpose:** the Invoices tab uses the same layout.
- **Steps:** click the **Invoices** tab.
- **Expected:** a wide card with a search box on the left, the invoice numbers side by side
  (`INV-00001` blue), and "100 of 886" (or similar) on the right. The invoice PDF fills the width below.
  Clicking `INV-00003` shows that invoice.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 4: Documents sidebar button
- **Purpose:** the button works when invoices exist.
- **Steps:** on Results, click **Data**, then click the document icon in the left sidebar.
- **Expected:** the Invoices tab opens and the document icon is highlighted.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

---

## Negative tests

### Test N1: Schema without invoices
- **Purpose:** no dead button.
- **Steps:** Start a new dataset → Describe your system → click the **Clinic appointments** example →
  **Draft schema**.
- **Expected:** the sidebar shows only the table and graph icons. There is **no** document icon, and after
  generating there is no Invoices tab.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test N2: Invoice search with no match
- **Steps:** Invoices tab → type `ZZZ` in the search box.
- **Expected:** the strip is empty and the right side reads "No invoice matches that ID."
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

---

## Known limitations

- Before a dataset is generated, the Tabular and Documents sidebar buttons are greyed out (hover
  explains "generate a dataset first"). This is intended.
- The invoice strip shows at most 100 invoices at a time. Use the search box for others.
- `invoice_items.item_id` values currently look like `INV-00001` (backend data format, reported to F).
