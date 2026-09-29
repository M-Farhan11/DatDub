# Deployment guide: backend on Railway, frontend on Vercel

- **For:** Farhan (F) · **Written by:** Haider (H) · **Date:** 2026-09-30
- **Branch to deploy:** `main` (contains the full frontend, H6 invoice PDFs and H7 ZIP export)
- **Result:** a public website (Vercel) that talks to a public API (Railway), which can
  read the Supabase demo database read-only.

```text
Visitor ──► Vercel (frontend, static files)
               │  HTTPS calls to VITE_API_URL
               ▼
           Railway (FastAPI backend, 1 process) ──► Gemini / Groq (schema + edge-case ideas only)
               │
               └── read-only ──► Supabase demo database (only when a user connects it)
```

> Roadmap note: Phase 10 (Deployment) is marked "LOCKED until Checkpoint 2 passes" in
> `roadmap.md`. Unlock it (or tick Checkpoint 2) before you start, so the docs match.

**Order matters:** 1) backend on Railway → 2) frontend on Vercel → 3) add the Vercel URL to
the backend's CORS → 4) test the whole demo. Plan about 30–45 minutes.

---

## Part 0: Before you start (5 min)

- [ ] `main` is up to date: `git checkout main; git pull`
- [ ] Backend tests pass locally:
  ```powershell
  cd backend
  .\.venv\Scripts\Activate.ps1
  pytest -q
  ```
  Expected: `186 passed, 6 skipped` (or more passed if you added tests).
- [ ] Frontend builds locally:
  ```powershell
  cd ..\frontend
  npm install
  npm run build
  ```
  Expected: `✓ built in …` and no errors.
- [ ] You have: a GitHub login with access to `M-Farhan11/DatDub`, a Railway account, a Vercel
  account, your Gemini + Groq API keys, and the Supabase `demo_reader` connection string.
- [ ] **Never** put keys or passwords in Git, in this file, or in chat. They only go into the
  Railway / Vercel dashboards.

---

## Part 1: Backend on Railway (15 min)

### 1.1 Create the service
1. Go to https://railway.com → **New Project** → **Deploy from GitHub repo**.
2. Pick **M-Farhan11/DatDub** (authorise Railway on GitHub if asked).
3. Open the new service → **Settings**:
   - **Source → Root Directory:** `backend`
   - **Source → Branch:** `main`
   - **Deploy → Custom Start Command:**
     ```text
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
     Use exactly **one** process (no `--workers`). Datasets live in memory; with several
     workers a dataset created by one worker would be "not found" on another.
   - **Deploy → Healthcheck Path:** `/api/health`
4. **Python version:** the backend is tested on Python 3.12. Pin it so Railway does not pick a
   different version: add a file `backend/.python-version` containing `3.12`, commit and push
   (your file ownership). Railway reads this file when it builds.

### 1.2 Environment variables
Service → **Variables** → **Raw Editor**, paste and fill in the `<…>` parts:

```env
APP_ENV=production
AI_PROVIDER=gemini
AI_FALLBACK_PROVIDER=groq
GEMINI_API_KEY=<your Gemini key>
GEMINI_MODEL=gemini-2.5-flash
GROQ_API_KEY=<your Groq key>
GROQ_MODEL=openai/gpt-oss-120b
AI_TIMEOUT_SECONDS=30
CORS_ORIGINS=http://localhost:5173
MAX_ROWS_PER_TABLE=100000
MAX_TOTAL_CELLS=8000000
MAX_STORE_CELLS=30000000
MAX_CONCURRENT_GENERATIONS=2
MAX_DATASETS=20
DATASET_TTL_MINUTES=60
ALLOW_PRIVATE_DB_HOSTS=false
DEFAULT_SAMPLE_LIMIT=200
MAX_SAMPLE_LIMIT=1000
```

Notes:
- **`GEMINI_MODEL`:** `gemini-2.5-flash` works with your existing key. A **new** Gemini key
  (created recently) gets `404 … no longer available to new users` for that model; in that
  case use `gemini-3.8-flash`. Haider hit this with his key (see TASKS.md → Requests).
- **`CORS_ORIGINS`:** keep `http://localhost:5173` for now; you add the Vercel URL in Part 3.
- **`ALLOW_PRIVATE_DB_HOSTS=false`** is required on Railway (SSRF guard: users cannot make the
  server connect to internal addresses).

### 1.3 Public URL
Service → **Settings → Networking → Generate Domain**. You get something like
`https://datdub-backend-production.up.railway.app`. Copy it; this is the **backend URL**.

### 1.4 Check the backend
Wait for the deploy to show **Active / Success**, then:

```powershell
curl https://<backend-url>/api/health
curl https://<backend-url>/api/templates
```
Expected: `{"status":"ok"}` and a list with `finance` and `ecommerce`.
Also open `https://<backend-url>/docs` in a browser: the Swagger page must load.

**One real AI call** (proves the keys work):
```powershell
curl -X POST https://<backend-url>/api/schema/from-prompt -H "Content-Type: application/json" -d '{\"prompt\":\"A library with members, books and loans\"}'
```
Expected: tables like `members`, `books`, `loans`. If the notes say "Mock AI…", `AI_PROVIDER`
is not set to `gemini`. A `503 ai_unavailable` means a wrong key or the provider is busy.

---

## Part 2: Frontend on Vercel (10 min)

### 2.1 Import the project
1. Go to https://vercel.com → **Add New… → Project** → import **M-Farhan11/DatDub**.
2. **Root Directory:** click **Edit** → choose `frontend`.
3. **Framework Preset:** `Vite` (auto-detected). Leave the defaults:
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Install Command: `npm install`
4. **Node.js version** (Project → Settings → General after the first import, or the build
   settings panel): **22.x**. Vite 8 needs Node 20.19+ or 22.12+.

### 2.2 Environment variables
In **Environment Variables** add (for Production, and Preview if you want preview links to work):

| Name | Value |
|---|---|
| `VITE_API_URL` | `https://<backend-url>` **no trailing slash, no `/api`** |
| `VITE_USE_FIXTURES` | `false` |
| `VITE_DEMO_DB_URL` | *(optional)* the Supabase **demo_reader** connection string |

About `VITE_DEMO_DB_URL`: any `VITE_…` value is baked into the public JavaScript that every
visitor downloads. Only ever use the **read-only `demo_reader`** login here, never an admin
or owner account. If you prefer not to publish it, leave it empty and paste the connection
string by hand during the demo (the "Use the demo database" button then simply does not appear).

### 2.3 Deploy
Click **Deploy**. When it finishes you get a URL like `https://datdub.vercel.app`
(Project → **Domains** shows it). Copy it; this is the **frontend URL**.

Settings → **Git → Production Branch** should be `main`.

> `VITE_…` variables are read at **build time**. After changing any of them, go to
> **Deployments → … → Redeploy**, otherwise the site keeps the old values.

---

## Part 3: Connect the two (3 min)

1. Railway → backend service → **Variables** → change `CORS_ORIGINS` to include the Vercel URL:
   ```env
   CORS_ORIGINS=https://datdub.vercel.app,http://localhost:5173
   ```
   (Use your real Vercel URL. No trailing slash. Add any custom domain here too.)
2. Railway redeploys automatically; wait for **Active**.
3. Open the frontend URL. Open the browser DevTools (F12) → **Console**: there must be **no**
   red "blocked by CORS policy" errors when you use the studio.

---

## Part 4: Test the canonical demo on the live URLs (10 min)

Open the **frontend URL** and run the full story:

| # | Step | Expected |
|---|---|---|
| 1 | Landing page loads | Headline "Test environments, not just fake data.", no console errors |
| 2 | **Open studio → Connect a database** → Connection string → paste the `demo_reader` URL (or **Use the demo database**) → **Connect** | Tables listed with row counts |
| 3 | Keep the default tables → **Structure + sample rows** → **Import** → **Review the schema** | "Imported N tables", then the schema graph |
| 4 | Click the `email` column | Column details: PII, AI confidence % |
| 5 | **Continue** → type 5000 rows → **Suggest** → tick 3 edge cases → **Generate data** | Generating screen, then "All checks passed" |
| 6 | **Checks** tab | Teal "Expected" tags on the rules the edge cases break; similarity % shown |
| 7 | **Invoices** tab → click an invoice | A real PDF; the items add up to the total |
| 8 | **Edge cases** tab | The 3 scenarios with affected IDs |
| 9 | **Continue to export → Download ZIP** | ZIP with tables, schema, report, ground truth, 20 PDFs |
| 10 | Landing → **Try the finance example** | Works without any database (offline fallback) |

Also try **Describe it** with a new idea (e.g. "a hospital with patients, doctors and
appointments") to prove the live AI works.

---

## Part 5: Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Site says "Could not reach the DatDub service" | `VITE_API_URL` wrong or backend down | Check `https://<backend-url>/api/health`; fix the variable; **Redeploy** on Vercel |
| Console: "blocked by CORS policy" | Vercel URL missing from `CORS_ORIGINS` | Add it exactly (https, no trailing slash) on Railway |
| Requests go to `http://127.0.0.1:8000` | `VITE_API_URL` was not set at build time | Set it, then Redeploy |
| "Dataset not found or expired" right after generating | More than one backend process/replica | One process, one replica, no `--workers` |
| "Mock AI: used the built-in … schema" note | `AI_PROVIDER` still `mock` | Set `gemini` on Railway |
| `503 ai_unavailable` | Bad key, wrong model name, or provider busy | Check keys; `gemini-3.8-flash` for new keys; Groq fallback set |
| `503 server_busy` | 2 generations already running | Wait a few seconds and retry (limit `MAX_CONCURRENT_GENERATIONS`) |
| "This database host is not allowed" | SSRF guard (expected for localhost/private IPs) | Use the Supabase pooler/public host |
| Vercel build fails on Node | Old Node version | Set Node 22.x in Vercel settings |
| Railway build uses the wrong Python | Version not pinned | `backend/.python-version` = `3.12` |

---

## Part 6: After it works

- [ ] Put both URLs in `TASKS.md` (F9 / H8) and in `project-state.md` (not the keys).
- [ ] Tick F9 and H8 only after Part 4 passes on the live URLs.
- [ ] Share the frontend URL with Haider and the presenter.
- [ ] Rollback if needed: Vercel → Deployments → pick the previous one → **Promote to
  Production**; Railway → Deployments → previous one → **Redeploy**.
- [ ] Remember: datasets are deleted after 60 minutes and after every backend restart/redeploy.
  Generate the demo dataset again shortly before presenting.
