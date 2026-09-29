# DatDub demo video: 3-minute script (screen recording + voice-over)

- **For:** Haider (H) · **Date:** 2026-09-30
- **Length:** about 3:00 (≈ 420 spoken words, calm pace)
- **Two flows:** 1) **Describe your system** (AI drafts a schema from text) · 2) **Upload CSV files**
- **Tip:** read Part A once so you understand the product, then record with Part C open on a second
  screen or on your phone.

---

## Part A: What DatDub is (learn this, say it in your own words)

**One sentence:** DatDub builds realistic, connected test databases, with deliberate edge cases
and proof that every row is valid, from a description, CSV files, a database or a template.

**The problem it solves**
- Teams cannot use real production data for testing (privacy, compliance, it takes weeks to get).
- Real data is also too "clean": it rarely contains the tricky cases that break software.
- Normal fake-data tools fill each column randomly. The rows do not fit together: an order points
  to a customer that does not exist, an invoice total does not match its items. Tests on that data
  prove nothing.

**What DatDub does, step by step**
1. **Source:** you describe your system in plain words, upload CSV files, connect a Postgres /
   Supabase database (read-only) or pick a template.
2. **Schema:** DatDub works out the tables, columns, keys, links between tables and business rules,
   and shows them as a graph. The AI marks personal data (PII) and shows how confident it is.
   You can correct anything.
3. **Configure:** you choose how many rows, a seed, how many empty or unusual values, and the
   AI suggests **edge cases** to add on purpose (e.g. a payment larger than its invoice).
4. **Generate + Results:** DatDub's own engine creates the data (the AI never writes rows), then
   checks every key, link and rule and shows a **validation report**. Edge cases appear as
   "Expected", with an **answer key** (ground truth) listing exactly which records were changed.
   Invoice tables become real **PDF invoices** whose totals add up.
5. **Export:** download every table as CSV or JSON, or one ZIP with the schema, the report, the
   answer key and invoice PDFs. The same seed always gives the same data.

**Why it is safe:** the AI only sees column names, types and summary statistics, never your
rows. Databases are opened read-only; sample rows are profiled and thrown away. Personal data is
always replaced with new fake values. Datasets are deleted after 60 minutes.

**Our line:** *"Test environments, not just fake data."*

---

## Part B: Before you record (checklist)

- [ ] Backend running **with real AI** (Gemini/Groq keys in `backend\.env`, `AI_PROVIDER=gemini`),
      started **without** `$env:AI_PROVIDER = "mock"`. Check http://127.0.0.1:8000/api/health.
      (Or use the deployed site once Farhan has deployed it.)
- [ ] Frontend running: `cd frontend` → `npm run dev` → http://localhost:5173
- [ ] Do **one full practice run** first (the AI's first call is the slowest), then refresh.
- [ ] Browser: zoom **100 %**, window about **1440 × 900**, close other tabs, hide bookmarks bar
      (Ctrl+Shift+B), turn off notifications.
- [ ] Keep the 4 CSV files ready in one folder: `Manual Testing\samples\customers.csv`,
      `invoices.csv`, `invoice_items.csv`, `payments.csv`.
- [ ] Copy this text so you can paste it (typing on camera is slow):
      `A hospital with patients, doctors, appointments and prescriptions. Each appointment has one patient and one doctor.`
- [ ] Recorder: OBS / Xbox Game Bar (Win+G) / Loom. Record the browser window, 30 fps.
- [ ] While the AI is "thinking" (5–20 s), keep talking or **cut the wait out** when editing.
- [ ] Backup: if the AI is slow or down, use **Load finance example** instead of Describe it and say
      "here I start from a ready-made template".

---

## Part C: The script

`[Click]` = what to do on screen · **Say** = voice-over. Times are a guide.

### 0:00 – 0:20 · Intro (landing page)
`[On screen]` Landing page at the top. Slowly scroll a little to the product preview, then back up.

**Say:**
"Every team needs test data, but real data can't be shared, and random fake data breaks as soon
as tables depend on each other. This is DatDub. It builds complete test environments, not just
fake data: connected tables, realistic edge cases, and proof that every row is valid."

`[Click]` **Open studio**.

---

### 0:20 – 1:35 · Flow 1: Describe your system

**0:20** `[On screen]` "Where should we start?"
**Say:** "I can start from a description, CSV files, a real database or a template. Let's describe a system."

`[Click]` The **Describe your system** box → paste the hospital text → **Draft schema**.

**Say (while it loads):** "Only my text goes to the AI. It drafts the tables, keys and rules, and I
review everything before any data is generated."

**0:40** `[On screen]` Review the schema: tables like patients, doctors, appointments, prescriptions.
**Say:** "Here is the schema as a graph. Every line is a real link, for example one patient has many
appointments. The blue note shows what the AI assumed."

`[Click]` The **email** (or **phone**) column in the patients table.
**Say:** "If I click a column, I see its type, that it is personal data, and how confident the AI is.
I can correct it. Personal data is always replaced with new fake values."

`[Click]` **Hide panel / Esc**, then **Continue**.

**0:58** `[On screen]` Configure.
`[Click]` **Medium 5,000** → **Suggest**.
**Say:** "I choose the size: five thousand patients. The seed makes the result repeatable. Now the
AI suggests edge cases for this schema: the tricky records that break real applications."

`[Click]` Tick **two** suggestions → **Generate data**.
**Say:** "I pick two. DatDub will insert exactly these, on purpose, and keep an answer key."

**1:15** `[On screen]` Generating → Results, **Checks** tab.
**Say:** "The data is generated by DatDub's engine, not by the AI, and then every key, link and rule
is checked. All checks passed. The teal 'Expected' rows are the edge cases I asked for."

`[Click]` **Edge cases** tab.
**Say:** "And this is the answer key: exactly which records were changed, and what my application
should do with them."

---

### 1:35 – 2:40 · Flow 2: Upload CSV files

`[Click]` **Continue to export → Start a new dataset → Start new**, then **Upload CSV files**.
(If you prefer, open a second browser tab with the studio already on this screen and switch to it.)

**1:40** `[Click]` Drag the 4 CSV files onto the drop zone → **Analyze 4 files**.
**Say:** "Now the second way: I upload four CSV files from an existing billing system:
customers, invoices, invoice items and payments."

**1:52** `[On screen]` Schema: 4 tables and 3 links.
**Say:** "DatDub linked the files on its own and found the business rules, like 'an invoice total
equals the sum of its line items' and 'a payment never exceeds its invoice'. It also learned the
statistics of my sample, so the new data will look like my real data, without copying it."

`[Click]` **Continue** → type **1000** in *Rows in customers* → **Generate data**.

**2:08** `[On screen]` Results → **Checks**.
**Say:** "All checks pass, and the similarity score shows how closely the new data follows my sample."

`[Click]` **Invoices** tab → click an invoice.
**Say:** "Because this is invoice data, DatDub also renders real PDF invoices from the generated rows.
The line items add up exactly to the total."

`[Click]` **Continue to export**.
**Say:** "Finally I export everything: every table as CSV or JSON, or one ZIP with the schema, the
validation report, the answer key and the invoice PDFs."

`[Click]` **Download ZIP** (let it download).

---

### 2:40 – 3:00 · Close
`[On screen]` Export page, or go back to the landing page hero.

**Say:**
"Your real data stays safe: the AI never sees rows, databases are opened read-only, and datasets
are deleted after an hour. The same seed always gives the same data, so your tests are
repeatable. DatDub: test environments, not just fake data."

`[End]` Hold the last frame 2 seconds.

---

## Part D: Terms you may need to explain

| Term | Simple meaning |
|---|---|
| **Synthetic data** | Data that is generated, not collected from real people. It looks real but is not. |
| **Schema** | The structure of a database: which tables exist, their columns and how they link. |
| **Table / row / column** | Like a spreadsheet sheet / one line / one field (e.g. `email`). |
| **Primary key (PK)** | The unique ID of each row, e.g. `customer_id`. |
| **Foreign key (FK) / link** | A column that points to another table's row, e.g. an invoice's `customer_id`. |
| **Referential integrity** | Every link points to a row that really exists. No "orphans". |
| **Business rule** | A rule the data must follow: invoice total = sum of items, due date after issue date, payment ≤ invoice. |
| **PII** | Personally identifiable information: names, emails, phone numbers, addresses. |
| **Semantic type ("Meaning")** | What a column really is (email, city, amount), not just text or number. |
| **AI confidence** | How sure the AI is about its guess for a column. Low = check it. |
| **Seed** | A number that makes the random generation repeatable. Same seed = same data. |
| **Empty / unusual values** | The share of blank cells and extreme numbers, to make data realistic. |
| **Edge case / scenario** | A tricky record added on purpose: duplicate payment, overpayment, leap-day date, missing email. |
| **Ground truth / answer key** | The list of exactly which records are edge cases, so tests know what to expect. |
| **Validation report** | The checks DatDub runs after generating: unique keys, valid links, types, every rule. |
| **Pass / Expected / Fail** | Pass = no problems · Expected = only your deliberate edge cases break it · Fail = unexpected problem. |
| **Similarity** | How closely the generated data's distribution matches your sample (CSV / database). |
| **Sample / profiling** | DatDub reads a small sample only to learn statistics, then discards it. |
| **Template** | A ready-made schema (Finance, E-commerce) to start quickly. |
| **Export / ZIP** | Download the data and all reports in one file. |

---

## Part E: Likely questions (short answers)

- **Does the AI make up the data?** No. The AI only reads the structure and suggests edge cases.
  DatDub's own engine generates every row, so it is fast, consistent and repeatable.
- **Is my data sent to the AI?** No rows, ever. Only column names, types and summary statistics.
- **Can it connect to our real database?** Yes, Postgres or Supabase, read-only. It reads the
  structure and optionally a small sample, then discards the sample.
- **How big can a dataset be?** Up to 100,000 rows per table.
- **What makes it different from a fake-data generator?** The data holds together (links and
  rules), includes deliberate edge cases with an answer key, and comes with proof (the report).
