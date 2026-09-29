# Frontend Test 1: Setup + the full studio flow (H0–H5, H6/H7 UI)

- **Date:** 2026-09-29
- **Author:** Haider (H), frontend
- **Branch:** `frontend` (not pushed yet at the time of writing)
- **What was built:** the whole DatDub website: a landing page and the studio,
  a 5-step flow (Source → Schema → Configure → Results → Export). You can start
  from a description, CSV files, a database or a template, review the tables
  on a graph, add tricky "edge case" records, generate data, check the quality
  report and download CSV files. Invoice PDFs and the ZIP download are not built
  yet; the site says "coming soon" for them.

> **Tip for the tester:** paste this whole file into any AI assistant and ask
> "explain this and help me run it step by step". Every step can be copied as-is.

---

## Part A: One-time setup (from zero)

You need **Windows PowerShell**, **Git**, **Node.js 20 or newer** and the backend
from `Manual Testing/backendtest1.md` (Part A there).

### A1. Install Node.js (skip if you have it)

1. Download the LTS version from https://nodejs.org and install with default options.
2. Check it in a new PowerShell window:
   ```powershell
   node --version
   ```
   Expected: `v20.x` or higher.

### A2. Get the code

```powershell
cd $HOME\Desktop\Ai-Hackathon      # the folder from backendtest1.md
git fetch
git checkout frontend
git pull
```

### A3. Install the frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
```
If `npm install` says "no space left on device", your C: drive is full. Use
another drive for the cache: `npm install --cache D:\npm-cache`.

### A4. Choose the mode in `frontend\.env.local`

Open `frontend\.env.local` in Notepad:
```powershell
notepad .env.local
```
- **Real backend (normal test):** set `VITE_USE_FIXTURES=false`
- **Sample data only (no backend needed):** set `VITE_USE_FIXTURES=true`

Leave `VITE_API_URL=http://127.0.0.1:8000`. Leave `VITE_DEMO_DB_URL` empty
unless Farhan or Haider gives you the read-only demo connection string privately.

### A5. Start both servers (two PowerShell windows)

**Window 1, backend** (see backendtest1.md for the Python environment):
```powershell
cd $HOME\Desktop\Ai-Hackathon\backend
.\.venv\Scripts\Activate.ps1
$env:AI_PROVIDER = "mock"
uvicorn app.main:app --port 8000
```
Check: open http://127.0.0.1:8000/api/health. Expected: `{"status":"ok"}`.

**Window 2, frontend:**
```powershell
cd $HOME\Desktop\Ai-Hackathon\frontend
npm run dev
```
Check: open http://localhost:5173. Expected: the DatDub landing page with the
headline "Realistic test data, ready in minutes."

Keep both windows open while testing. Closing a window stops that server.

---

## Part B: Tests

Do them in order. Write PASS or FAIL and a short note.

### Test 1: Landing page
- **Purpose:** the entry page looks right and its buttons work.
- **Steps:** open http://localhost:5173. Scroll down. Click **How it works** in the top bar.
  Scroll back up and click **Open studio**.
- **Expected:** soft moving shapes behind the headline; a studio preview with 4 tables
  joined by dashed lines; "From idea to test database in three steps"; the page
  scrolls to that section when you click How it works; Open studio shows
  "Where should we start?" with 4 cards.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 2: Sidebar and logo
- **Purpose:** the studio navigation works.
- **Steps:** hover each icon in the left sidebar. Click the arrow at the bottom of
  the sidebar, then click it again. Click the DatDub logo at the top of the sidebar.
- **Expected:** tooltips "Tabular", "Relational", "Documents"; the sidebar widens and
  shows labels, then narrows again; the logo returns to the landing page.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 3: Finance example (main path)
- **Purpose:** the fastest way into the product loads a real schema.
- **Steps:** on the landing page click **Try an example**.
- **Expected:** after a moment, "Review the schema" with a graph of 4 tables
  (customers, invoices, invoice_items, payments) and lines labelled like
  "1 customer has 1 to 8 invoices". Step 2 "Schema" is active in the top bar.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 4: Column details
- **Purpose:** you can inspect and correct a column.
- **Steps:** in the graph, click the `email` row in the customers card. Change
  **Meaning** to "Generic string", click **Save** (Reset and Save become disabled again).
  Press **Escape**.
- **Expected:** the right panel shows "Column details", an "AI confidence" percentage,
  PII tag, toggles. After Save you see "Saved". Escape returns to "Business rules"
  (7 rules for the finance template).
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 5: Configure and edge cases
- **Purpose:** settings and edge-case suggestions work.
- **Steps:** click **Continue**. Click the **Medium 5,000** preset. Click
  **Suggest**. Tick the first 3 suggestions. Change one count with the + button.
- **Expected:** rows for customers becomes 5000 and a hint estimates the linked
  tables; 5 suggestions appear, each with "Expected: …"; the footer shows
  "3 selected · N records".
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 6: Generate
- **Purpose:** data generation finishes and shows results.
- **Steps:** click **Generate data**.
- **Expected:** a "Generating finance_demo" card with a ticking checklist, then
  (about 5–15 seconds) the Results page with "All checks passed" and
  "seed 42 · … rows · 4 tables · 3 edge cases".
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 7: Results tabs
- **Purpose:** every results tab shows its content.
- **Steps:** look at **Checks**. Open **Data**, click `payments`, click **Next** twice.
  Open **Edge cases**, click **View rows** on one card. Open **Invoices**, type
  `INV-00042` in the search box.
- **Expected:** Checks shows stat cards and a table with green "Pass" and teal
  "Expected" tags plus a legend; Data shows 50 rows per page with "Showing 101–150 of …";
  some rows have a small teal dot; View rows jumps to the Data tab on that table;
  Invoices lists IDs and the search finds INV-00042; the preview says
  "Invoice preview is coming soon" (not built yet, this is expected).
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 8: Export
- **Purpose:** downloads work.
- **Steps:** click **Continue to export**. Click **CSV** next to `customers`.
  Click **Download ZIP**. Click **Copy** on "To recreate this dataset".
- **Expected:** `customers.csv` downloads and opens in Excel with 5,000 rows;
  the ZIP shows "ZIP export is coming soon" (expected for now); Copy shows "Copied".
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 9: Describe it
- **Purpose:** a schema can be drafted from text.
- **Steps:** click **Start a new dataset** → **Start new**. Click **Describe it**,
  click the **Online store** chip, click **Draft schema**.
- **Expected:** the Schema step opens with tables such as customers, orders,
  order_items, payments and a blue note bar with the AI's assumption.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 10: Upload CSV files
- **Purpose:** CSV upload builds a linked schema.
- **Steps:** Change source → **Upload CSV files**. Drag the 4 files
  `customers.csv`, `invoices.csv`, `invoice_items.csv`, `payments.csv` from
  `Manual Testing\samples\` onto the drop zone. Click **Analyze 4 files**.
- **Expected:** the files are listed with sizes; the Schema step shows 4 tables with 3 links.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 11: SQLite file
- **Purpose:** the database flow works with a file.
- **Steps:** Change source → **Connect a database** → **Upload SQLite file**, choose
  `Manual Testing\samples\finance_demo.sqlite`, **Continue**, keep
  "Structure + sample rows", click **Import tables**, then **Review the schema**.
- **Expected:** "Imported 4 tables" with the number of sampled rows; the Schema step
  opens with "profiled from … sample rows" under the title.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

---

## Part C: Negative tests (bad input should give a clear message, never a crash)

### Test 12: Empty CSV
- **Steps:** Upload CSV files → add `Manual Testing\samples\empty.csv` → Analyze.
- **Expected:** a red box "The files could not be analyzed" with "empty.csv is empty."
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 13: Fake SQLite file
- **Steps:** Connect a database → Upload SQLite file → `fake.sqlite` → Continue → Import.
- **Expected:** a red box saying the file is not a SQLite database.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 14: Local database is blocked
- **Steps:** Connect a database → Connection string →
  `postgresql://reader:secret@127.0.0.1:5432/postgres` → Connect.
- **Expected:** a red box "Could not connect" explaining that private and local
  addresses are blocked. The password is never shown in the message.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 15: Wrong connection string format
- **Steps:** type `mysql://x@y/z` in Connection string.
- **Expected:** "Use a Postgres URL that starts with postgresql://" and the Connect button stays disabled.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 16: Too many rows
- **Steps:** load the finance example, go to Configure, type `200000` in Rows in customers,
  click **Generate data**.
- **Expected:** an orange "Large job" warning before you click; after clicking,
  a red box "Max 100,000 rows per table …" and you stay on Configure.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 17: Backend stopped
- **Steps:** stop the backend (Ctrl+C in Window 1), then click **Try the finance example**.
- **Expected:** "Could not reach the DatDub service. Check that the backend is running and try again."
  Start the backend again afterwards.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

---

## Part D: Known limitations (not bugs)

- Invoice PDFs and the ZIP download show "coming soon" (tasks H6 and H7).
- "Use the demo database" only appears when `VITE_DEMO_DB_URL` is set in `.env.local`.
- A database on your own computer (localhost) cannot be used from the website; this
  is a security rule. Use the SQLite upload or a public database such as Supabase.
- Refreshing the browser starts over: nothing is saved, on purpose.
- Generated datasets are deleted after 60 minutes; opening an old one shows
  "This dataset has expired. Generate it again."
- The layout is built for laptop and desktop screens (1024 px and wider).
