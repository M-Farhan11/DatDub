# Backend Test 5: Real AI end to end (no mock data)

- **Date:** 2026-09-30
- **Author:** Farhan (F), backend
- **Branch:** `F/phasef9`
- **What this session fixed:**
  1. **"Always the same mock data":** the frontend was in sample-data mode
     (`VITE_USE_FIXTURES=true` in `frontend/.env.local`), and the old setup step
     forced `AI_PROVIDER=mock`. With both off, your own description drives the data.
  2. **Numbers follow the range you ask for:** before, "GPA between 0 and 4" gave
     GPA 4.0 on almost every row. Now values spread across the whole range.
  3. **Realistic text values:** columns like `diagnosis`, `vaccine_name` or
     `course_name` now get real domain values (e.g. "Rabies", "Calculus I") instead
     of random words. Values you name yourself (e.g. "dog/cat/rabbit") are kept exactly.

> **Tip for the tester:** paste this whole file into any AI assistant and ask
> "explain this and help me run it step by step".

---

## Setup

Full setup from zero: `Manual Testing/backendtest1.md` (Part A) and
`Manual Testing/frontendtest1.md` (Part A). **Two differences for this test:**

1. In `frontend\.env.local` set:
   ```
   VITE_USE_FIXTURES=false
   ```
   (Restart `npm run dev` after changing it.)
2. Start the backend **without** `$env:AI_PROVIDER = "mock"`. Open a **new**
   PowerShell window (so no old setting is left over):
   ```powershell
   cd $HOME\Desktop\Ai-Hackathon\backend
   .\.venv\Scripts\Activate.ps1
   uvicorn app.main:app --port 8000
   ```
   `backend\.env` must contain `AI_PROVIDER=gemini`, `AI_FALLBACK_PROVIDER=groq`
   and both API keys (ask Farhan privately; never paste keys into this file).

Check: http://127.0.0.1:8000/api/health gives `{"status":"ok"}`.

---

## Tests

### Test 1: Your description decides the tables
- **Purpose:** the schema comes from the AI reading your text, not from a fixed sample.
- **Steps:** open http://localhost:5173 → **Open studio** → **Describe it** → paste:
  ```
  A veterinary clinic: pet owners, their pets (species dog/cat/rabbit, weight in kg), vet appointments with a diagnosis and a fee in PKR, and vaccinations given to each pet.
  ```
  → **Draft schema** (takes 5–30 seconds).
- **Expected:** "Review the schema" with tables about owners, pets, appointments and
  vaccinations (names may vary slightly each time). Business rules include
  "Allowed values: pet.species". **No** customers/invoices tables.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 2: A second, different description gives a different schema
- **Purpose:** proves the data is not canned.
- **Steps:** **Change source** → **Describe it** → paste:
  ```
  A university: students with a GPA between 0 and 4, courses with credit hours 1 to 4, and enrollments where each student gets a letter grade A, B, C, D or F.
  ```
  → **Draft schema**.
- **Expected:** tables for students, courses and enrollments. Rules: range on `gpa`
  (0–4), range on `credit_hours` (1–4), allowed values on `grade` (A–F).
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 3: Generated rows respect what you asked
- **Purpose:** the values really follow the description.
- **Steps:** continue from Test 2 → **Continue** → click **Small 500** → **Generate data**
  → **Data** tab → look at each table.
- **Expected:**
  - `gpa` values are spread between 0 and 4 (e.g. 0.8, 2.61, 3.47), **not** 4.0 on every row
  - `credit_hours` shows 1, 2, 3 and 4
  - `grade` only shows A, B, C, D, F
  - `course_name` looks like real course names (e.g. "Calculus I")
  - Results header says "All checks passed"
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 4: Edge cases follow your instruction
- **Purpose:** the AI edge-case suggestions use your words.
- **Steps:** repeat Test 1, **Continue**, **Small 500**. In "What should the data test?" type
  `Pets with extreme weights and appointments with zero fee` → **Suggest**.
- **Expected:** suggestions about pet weight extremes and appointment fees, each with
  an "Expected: …" line. Tick 3, **Generate data** → "All checks passed" and the
  rules on weight/fee show teal **Expected** tags (the planted records).
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 5: Swagger check (optional, for developers)
- **Steps:** open http://127.0.0.1:8000/docs → `POST /api/schema/from-prompt` →
  **Try it out** → body:
  ```json
  {"prompt": "A gym: members with a membership plan basic/premium/vip, and check-ins with a timestamp"}
  ```
  → **Execute**.
- **Expected:** `200`; `schema.tables` contains members and check-ins; a rule with
  `allowed_values` `["basic","premium","vip"]`.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

---

## Negative tests

### Test 6: Empty description
- **Steps:** Describe it → leave the box empty.
- **Expected:** **Draft schema** stays disabled (or a clear message); no crash.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 7: AI unavailable
- **Steps:** stop the backend, set invalid keys in `backend\.env`
  (`GEMINI_API_KEY=bad`, `GROQ_API_KEY=bad`), start it again, repeat Test 1.
  **Put the real keys back afterwards.**
- **Expected:** a red message "The AI service is unavailable right now. Try again or
  start from a template." Templates (Try an example) still work.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

---

## Known limitations (not bugs)

- The AI's answers vary: table and column names can differ a little on each run.
  That is normal. What matters is that they match the description.
- The Gemini free tier has a daily quota. When it runs out, Groq answers instead
  (slower, same result). You will not see a difference in the UI.
- Pet weights use the whole range the AI chose (e.g. 0.1–200 kg), so a 150 kg cat
  can appear. Ranges are respected, but no per-species realism yet.
- Free-text names (e.g. pet names) can still be random words.
- ZIP download shows "ZIP export is coming soon" (Haider's task H7).
- In Column details, pressing **Escape** right after **Save** does not close the
  panel; click a field first, then Escape. Reported to Haider.
