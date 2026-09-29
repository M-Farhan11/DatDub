# TASKS — Shared Work Tracker

> **Read this first every session.** It is the single source of truth for
> who owns what, what is done and what is left.
> Farhan = **F** (backend lead) · Haider = **H** (frontend lead + 2 backend modules)
> Presentation is handled by the 3rd member and is not tracked here.

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done (run + verified) · `[!]` blocked

---

## 1. Sync protocol (both of you, every session)

1. **Start:** `git pull --rebase`, read this file, and check **Requests** (section 7).
2. **Work only on your own tasks and your own files** (section 2).
3. Need something from the other person? Add it to **Requests** and do not
   edit their files.
4. **Before pushing:** run `pytest` (backend) and/or `npm run build`
   (frontend), then `git pull --rebase`, then push. Commit prefix `[F]` / `[H]`.
5. **End of session:**
   - update your task checkboxes below,
   - add one line to the **Session Log** (section 9),
   - update `project-state.md`,
   - commit and push.
6. Tell Claude Code at the start: *"I am Farhan"* or *"I am Haider"*.

---

## 2. File ownership (never edit the other person's files)

| Path | Owner |
|---|---|
| `backend/app/ai/**` | F |
| `backend/app/schemas/**` (API contract models) | F |
| `backend/app/ingest/**` (CSV, prompt, DB/SQLite inference, profiler) | F |
| `backend/app/engine/**` (generator, dataset store) | F |
| `backend/app/validation/**` | F |
| `backend/app/scenarios/**` | F |
| `backend/app/templates/**` | F |
| `backend/app/api/{templates,schema,scenarios,generate,datasets}.py` | F |
| `backend/app/main.py`, `backend/app/core/**`, `backend/requirements.txt`, `backend/.env.example` | F |
| `backend/tests/**` except the two Haider files below | F |
| `scripts/seed_demo_db.sql` | F |
| `docs/api-contract.md`, `frontend/src/api/types.ts` | F (changes need both to agree) |
| `Manual Testing/backendtest*.md` (+ backend samples in `Manual Testing/samples/`) | F |
| `Manual Testing/frontendtest*.md` | **H** |
| `backend/app/documents/**` (invoice PDF) | **H** |
| `backend/app/export/**` (ZIP export) | **H** |
| `backend/app/api/documents.py`, `backend/app/api/export.py` | **H** |
| `backend/tests/test_documents.py`, `backend/tests/test_export.py` | **H** |
| `frontend/**` (everything except `src/api/types.ts`) | **H** |
| `TASKS.md`, `project-state.md` | both (only your own sections + log lines) |
| `CLAUDE.md`, `idea.md`, `architecture.md`, `design.md`, `roadmap.md` | F (H via Requests) |

**Shared interface between F and H in the backend** (F provides it in F0):

```python
# backend/app/engine/store.py
def get_dataset(dataset_id: str) -> GeneratedDataset  # raises DatasetNotFound
# GeneratedDataset: dataset_id, schema: DatasetSchema,
#   tables: dict[str, pandas.DataFrame], report: ValidationReport,
#   ground_truth: list[GroundTruthEntry]
```

H's documents/export code **only reads** through `get_dataset()`. It never
imports engine internals.

---

## 3. Timeline (8 hours)

| Time | Block | Goal |
|---|---|---|
| 0:00–0:45 | **H0 Contract freeze** | Contract, stubs, scaffold. Both unblocked. |
| 0:45–3:30 | **Core** | Template/CSV/prompt → schema → generate → preview → report |
| 3:30–4:00 | **Checkpoint 1** | End-to-end on real backend, merged on `main` |
| 4:00–6:00 | **Differentiators** | DB connect (Supabase), scenarios + ground truth, invoice PDF, ZIP |
| 6:00–6:45 | **Integration + deploy** | Railway + Vercel, canonical demo on deployed URLs |
| 6:45–7:30 | **Stretch** | Only if everything above is `[x]` |
| 7:30–8:00 | **Freeze** | Bug fixes only; rehearse the demo with the presenter |

**Canonical demo (everything serves this):**
Connect Supabase DB → schema graph appears → "Add realistic edge cases for
testing" → tick scenarios → generate 5,000 rows → quality report (integrity
100%, rules pass, N injected-as-expected, similarity %) → open synthetic
invoice PDF → ground truth tab → download ZIP.
**Offline fallback:** Finance template + `AI_PROVIDER=mock`.

---

## 4. FARHAN (F): Backend core

### F0 · Contract freeze and repo setup (0:00–0:45) — BLOCKS HAIDER, do first
- [x] `git init` (branch `main`) + first commit (docs + bootstrap)
- [x] Create GitHub repo, push, add Haider as a collaborator
- [x] Pydantic contract models in `backend/app/schemas/`: `DatasetSchema`,
      `TableSchema`, `ColumnSchema`, `ForeignKey`, `Rule`, `ColumnProfile`,
      `GenerateRequest`, `GenerateResponse`, `ScenarioProposal`,
      `ScenarioSelection`, `ValidationReport`, `GroundTruthEntry`, `DocumentHints`
- [x] `docs/api-contract.md`: fill in the exact JSON for each endpoint
- [x] `frontend/src/api/types.ts`: a TS mirror of the contract models
- [x] `backend/app/engine/store.py`: in-memory `save_dataset` / `get_dataset`
- [x] Stub routers for all endpoints (returning Mock/fixture data), including
      `api/documents.py` + `api/export.py` stubs (then handed to H)
- [x] `main.py`: register all routers, CORS (`CORS_ORIGINS` env), `/api` prefix
- [x] `requirements.txt`: `pandas numpy faker sqlalchemy psycopg[binary] python-multipart google-genai reportlab`
- [x] `.env.example`: `GEMINI_MODEL`, `GROQ_MODEL`, `CORS_ORIGINS`,
      `MAX_ROWS_PER_TABLE=100000`, `MAX_DATASETS=20`, `DATASET_TTL_MINUTES=60`,
      `ALLOW_PRIVATE_DB_HOSTS=true` (local; `false` on Railway),
      `DEFAULT_SAMPLE_LIMIT=200`, `MAX_SAMPLE_LIMIT=1000`
- [x] Store: TTL 60 min + max 20 datasets (oldest evicted); `dataset_id` = random, unguessable (`secrets.token_urlsafe`)

**Accept:** `uvicorn` runs; `/docs` shows every endpoint; each stub returns
contract-valid JSON; `pytest` is green; pushed to `main`.

> F0 notes: `/api/generate` already runs a first-cut engine
> (`engine/generator.py`: FK-correct, seeded, applies date_order /
> sum_of_children / lte_parent) and `validation/checks.py` does PK + FK
> checks, so Haider gets real data for PDF/ZIP. F5/F6 harden them. Known
> gap for F5: child tables are not capped yet (100k customers → ~1.5M items).

### F1 · AI layer (0:45–1:30)
- [x] `AIService.generate_structured(prompt, response_model)`: validate with
      Pydantic, retry once on invalid output, then fallback provider, then `AIProviderError`
- [x] `GeminiProvider` (google-genai, structured output, model from env)
- [x] `GroqProvider` (httpx → OpenAI-compatible endpoint, JSON mode + schema in prompt, model from env)
- [x] `MockProvider`: canned valid objects for `SchemaDraft`, `SemanticEnrichment`, `ScenarioPlan`
- [x] `backend/app/ai/prompts.py`: prompt → schema, column semantics, scenario proposals

**Accept:** tests pass with mock; with a real key, one call returns a valid
object; invalid JSON triggers retry/fallback (tested with a fake provider).

> F1 notes: `app/ai/validate.py` converts AI output to contract models and
> drops/repairs bad references (`draft_to_schema`, `apply_enrichment`,
> `validate_proposals`). F3 CSV/DB ingest should call
> `prompts.semantic_enrichment_prompt(tables)` with a privacy-filtered payload,
> then `apply_enrichment`. Live check: set `GEMINI_API_KEY` + `GEMINI_MODEL`
> (or Groq), then run `pytest tests/test_ai_live.py -v`.

### F2 · Templates (1:30–1:50)
- [x] `ecommerce`: customers → orders → order_items, orders → payments, with rules
      (`sum_of_children` order.total, `date_order` created_at ≤ order_date ≤ paid_at,
      `lte_parent` payment.amount ≤ order.total, `allowed_values` status)
- [x] `finance`: customers → invoices → invoice_items, invoices → payments, with
      the same kinds of rules plus `document_hints` for the invoice PDF
- [x] `GET /api/templates`, `GET /api/templates/{id}`

**Accept:** both templates load and pass contract validation, with no AI involved.

### F3 · Ingest / schema inference (1:50–2:40)
- [x] CSV (1..n files): pandas dtype + regex heuristics (email, phone, date,
      id, currency) + PK guess + FK guess across files (`<table>_id` naming)
      + AI semantic enrichment on **metadata only**
- [x] Prompt → schema via AI; validate (unique names, FK targets exist, rules reference real columns)
- [x] DB step A: `POST /api/db/tables`: accepts a URL **or** host/port/db/user/password;
      returns tables + column counts + `estimated_rows` (`pg_class.reltuples`) + FK references. **No rows read.**
- [x] DB steps B+C: `POST /api/schema/from-db {connection, tables, mode, sample_limit}`
      via SQLAlchemy `inspect()`:
  - FK parent tables auto-added (returned in `auto_added`)
  - `sample_limit` default 200, max 1000
  - `TABLESAMPLE SYSTEM` for big tables, `ORDER BY random() LIMIT` for small ones
  - profile the sample, then discard the rows
- [x] `POST /api/schema/from-sqlite` (upload; same modes; temp file deleted after the request)
- [x] DB safety (`ingest/db_guard.py`):
  - Postgres-only scheme
  - SSRF guard: resolve the host, reject loopback/private/link-local/metadata IPs unless `ALLOW_PRIVATE_DB_HOSTS=true`
  - `connect_timeout=5`, `SET TRANSACTION READ ONLY`, `statement_timeout=10s`
  - credentials redacted from every error/log and never stored
  - error codes: `db_unreachable`, `db_auth_failed`, `db_host_not_allowed`, `db_timeout`, `db_unsupported_dialect`
- [x] AI payload builder: names, types, constraints and aggregates only; category
      values only for columns with < 20 distinct values that are not PII.
      Unit test: no sample value from a PII column appears in the AI request.

**Accept:** each input returns a valid `DatasetSchema`; a column profile is
attached when sample rows exist; bad URL/file → a clean 4xx with a message;
`127.0.0.1` / `169.254.169.254` are rejected when `ALLOW_PRIVATE_DB_HOSTS=false`;
a password never appears in a response or log (tested).

> F3 notes: code in `app/ingest/` (`heuristics`, `profiler`, `build` = shared
> finalize step, `csv`, `database`, `db_guard`, `enrich` = AI payload + merge,
> `rules` = CSV rule inference: allowed_values, date_order, sum_of_children,
> lte_parent). Verified: CSV, SQLite (both modes), guard + error mapping
> (incl. a real local Postgres auth failure). `tests/test_ingest.py::test_postgres_end_to_end`
> runs only with `TEST_PG_URL` set; not yet run against Supabase (F8).
> Row-count hints are capped at 1000 (the user raises counts in Configure).

### F4 · Profiler (inside F3 time)
- [x] Per column: null %, min/max/mean/std, 10-bin histogram, top category
      frequencies, uniqueness ratio. Per FK: children-per-parent distribution.

### F5 · Generation engine (2:40–3:30) — the heart of the product
- [ ] Topological order over FKs; parents first
- [ ] Column generators by semantic type, **vectorized**:
  - NumPy for numerics/dates/categoricals (from profile or rule ranges, profile weights / `allowed_values`)
  - **value pools** for text PII: seeded Faker pre-generates ~5k names/streets/companies, then vectorized random picks. No per-row Faker calls.
  - emails = name + sequence, so they are unique
  - child FK columns sample parent PKs that were already generated
- [ ] Child counts per parent from the profile distribution or a default Poisson
- [ ] Rules enforced: derived totals computed from children, dates ordered, `lte_parent` capped
- [ ] Null rate + outlier rate (nullable / numeric columns only)
- [ ] Seed → fully reproducible; `MAX_ROWS_PER_TABLE` cap (default 100k,
      hard ceiling 500k) → `422 rows_limit_exceeded` above it
- [ ] `POST /api/generate` saves to the store and returns previews (50 rows/table) + report
- [ ] `GET /api/datasets/{id}/tables/{t}?offset&limit`

**Accept:** finance template with 5,000 customers generates in under 5 s and
100,000 customers in under 30 s; the same seed gives identical output; FK
integrity is 100%. AI is called 0 times during generation (plans only).

### F6 · Validation report (inside Core / by Checkpoint 1)
- [ ] PK uniqueness, FK integrity, type/nullability, per-rule pass/fail counts
- [ ] Injected scenario violations counted as **expected**, not failures
- [ ] Similarity vs profile when a sample exists (category TVD, numeric
      histogram overlap → 0–100%)

**Accept:** a clean generation reports all PASS; an intentionally broken row
shows up as FAIL in a unit test.

### ✅ CHECKPOINT 1 (3:30–4:00) with Haider: template → generate → preview → report on the real backend

### F7 · Scenario Studio backend (4:00–5:00)
- [ ] Catalogue: `null_burst`, `extreme_value`, `duplicate_record`,
      `boundary_date`, `rule_violation`
- [x] `POST /api/scenarios/propose {schema, instruction}` → AI proposals,
      validated against the schema (invalid ones dropped)
- [ ] Injection after generation + `GroundTruthEntry` per scenario
      (`scenario`, `table`, `affected_ids`, `description`, `expected_behavior`)

**Accept:** selecting 3 scenarios gives exactly those records in ground
truth, and the report marks them as expected.

### F8 · Supabase demo source DB (5:00–5:40)
- [ ] `scripts/seed_demo_db.sql`: finance/e-commerce tables, ~300 rows, a few natural edge cases
- [ ] Create a Supabase project, run the seed, add a **read-only** role for the demo
- [ ] Verify `from-db` (both modes) against Supabase and a local Postgres

### F9 · Deploy backend (6:00–6:45)
- [ ] Railway service from `backend/`, env vars set, CORS includes the Vercel URL
- [ ] Run the canonical demo against the deployed URL

---

## 5. HAIDER (H): Frontend + documents/export backend modules

> Until Farhan's endpoints are real, build against **fixtures mode**
> (`VITE_USE_FIXTURES=true`) using JSON that matches `docs/api-contract.md`.
> You can also run the backend locally with `AI_PROVIDER=mock`.

### H0 · Scaffold (0:00–0:45)
- [ ] `frontend/`: Vite + React + TS + Tailwind + shadcn/ui; install
      `@xyflow/react`, `@tanstack/react-table`
- [ ] App shell: left workspace nav (Tabular / Relational / Documents, matching
      the PDF's design) + 5-step stepper: **Source → Schema → Configure → Results → Export**
- [ ] `src/api/client.ts` (uses `VITE_API_URL`) + `src/api/fixtures/*.json` + fixtures toggle
- [ ] Global state for the current `DatasetSchema`, config and `dataset_id` (React context or zustand; keep it simple)

**Accept:** `npm run dev` shows the shell; `npm run build` passes; pushed.

### H1 · Source step (0:45–1:45)
- [ ] Tabs: **Prompt** (textarea + example chips) · **CSV** (drag-drop, multi-file) ·
      **Database** (see below) · **Templates** (E-commerce, Finance cards)
- [ ] **Database tab**, a 3-step mini-flow:
  1. **Connect:** toggle "Connection string" / "Fields" (host, port, database, user, password) + a SQLite upload option → `POST /api/db/tables`
  2. **Pick tables:** checklist with column count, `~estimated_rows`, FK links; mode toggle "Schema only / Schema + sample"; sample size (default 200, max 1000)
  3. **Extract** → `POST /api/schema/from-db` → show an "auto-added: …" notice if any
  - Credentials live in **React state only** (never `localStorage`) and are re-sent with each call
  - Collapsible help: "Use a read-only user" with the SQL snippet; "Local DBs (localhost) aren't reachable from the hosted app, so use a tunnel or run locally"
  - A "Use demo database" button pre-fills the Supabase read-only demo connection
- [ ] Configure step shows a "large job" warning above 100k rows
- [ ] Loading + error states; on success → store the schema → go to the Schema step

### H2 · Schema step (1:45–2:45) — main visual "wow"
- [ ] React Flow graph: one node per table (columns listed, PK/FK icons),
      FK edges labelled `1:N`, auto layout (simple left-to-right by FK depth)
- [ ] Field inspector side panel on column click: type, semantic type,
      PII badge, AI confidence %, editable semantic type dropdown + PII toggle
- [ ] Rules list under the graph (human-readable)

### H3 · Configure step (2:45–3:15)
- [ ] Rows per table (root table count; children derived), seed, null %, outlier %, locale
- [ ] "Generate" button → `POST /api/generate` → Results

### H4 · Results step (3:15–3:30, polish after the checkpoint)
- [ ] Table tabs + TanStack Table preview (paging via `/datasets/{id}/tables/{t}`)
- [ ] Quality report cards: overall PASS/FAIL, PK uniqueness %, FK integrity %,
      rules passed x/y, rows generated, injected scenarios (expected), similarity % if present

### ✅ CHECKPOINT 1 (3:30–4:00) with Farhan

### H5 · Scenario Studio UI (4:00–4:45)
- [ ] In Configure: instruction box ("Add realistic edge cases for testing") →
      **Propose** → checklist of proposals (title, table, description, count input)
- [ ] Selected scenarios are sent in `GenerateRequest.scenarios`
- [ ] Results → **Ground Truth** tab: scenario, table, affected IDs, expected behaviour

### H6 · Invoice PDF, backend + UI (4:45–5:30)
- [ ] `backend/app/documents/invoice_pdf.py` (ReportLab): header, billed-to,
      line items, tax, total, matching the PDF's invoice design; uses
      `schema.document_hints` to map the invoice / item / customer tables
- [ ] `backend/app/api/documents.py`: `GET /api/datasets/{id}/documents/invoices` (list IDs) +
      `GET /api/datasets/{id}/documents/invoices/{invoice_id}.pdf`
- [ ] `backend/tests/test_documents.py` (generate the finance template → PDF bytes start with `%PDF`)
- [ ] UI **Documents** tab: invoice picker + `<iframe>` PDF preview

**Accept:** the invoice total in the PDF equals the sum of its items in the data.

### H7 · ZIP export, backend + UI (5:30–6:00)
- [ ] `backend/app/export/zip_export.py`: `tables/*.csv`, `tables/*.json`,
      `schema.json`, `validation_report.json`, `ground_truth.json`,
      `documents/invoices/*.pdf` (first 20)
- [ ] `backend/app/api/export.py`: `GET /api/datasets/{id}/export.zip`
- [ ] `backend/tests/test_export.py`
- [ ] Export step: download ZIP button + per-table CSV download

### H8 · Deploy frontend (6:00–6:45)
- [ ] Vercel project from `frontend/`, `VITE_API_URL` = the Railway URL
- [ ] Run the canonical demo on the deployed URLs with Farhan

### H9 · Polish (anytime there is slack)
- [ ] Empty states, toasts, disabled buttons while loading, "Load demo" shortcut buttons

---

## 6. Integration checkpoints (both)

- [ ] **Checkpoint 1 (3:30):** template → generate → preview → report, real backend
- [ ] **Checkpoint 2 (6:00):** DB connect → scenarios → PDF → ZIP, real backend
- [ ] **Deployed demo (6:45):** canonical demo on Vercel + Railway + Supabase
- [ ] **Freeze (7:30):** tag `demo`, no new features

---

## 7. Requests (cross-owner changes, contract changes, new deps)

Format: `- [ ] YYYY-MM-DD HH:MM · FROM → TO · what · why`

- [ ] 2026-09-29 · F → H · `backend/app/api/documents.py` + `export.py` stubs are in place (invoice list is real; PDF/ZIP return `501 not_implemented`). They are yours from now on. Read data only via `app.engine.store.get_dataset()`; rows → JSON via `app.engine.generator.to_records(df)`.

---

- [ ] 2026-09-29 · F → H · FYI (additive, no shape change): F3 added error codes `invalid_csv` (400) and `invalid_sqlite_file` (400); `from-sqlite` with unknown tables returns `404 table_not_found`; bad `mode` → 422. DB errors are 400 (`db_unsupported_dialect` 422). Please show `error.message` as-is in the UI. OK to add these codes to the list in `docs/api-contract.md`?
- [ ] 2026-09-29 · F → H · New rule in `CLAUDE.md` (Manual QA Test Rule): at the end of each session write `Manual Testing/frontendtest<N>.md` for our QA member. `frontendtest1.md` must include full setup (Node, `npm install`, `.env`, `npm run dev`, backend start: see `Manual Testing/backendtest1.md` Part A).

---

## 8. Enhancements backlog (ONLY after all MUST-HAVE tasks are `[x]`)

Priority order. Claim one by writing your initial next to it.

1. [ ] Record inspector: click a customer → follow FK → orders → payments (H, F: endpoint)
2. [ ] Similarity charts, synthetic vs sample histograms (Recharts) (H)
3. [ ] Natural-language rule box → AI maps it to the rule catalogue (F + H)
4. [ ] Bank statement document with running balance + CSV (H backend, F data)
5. [ ] SQL `INSERT` export in the ZIP (H)
6. [ ] N:N junction-table cardinality (F)
7. [ ] Column privacy controls: mask/hash values learned from the sample (F + H)
8. [ ] SDMetrics diagnostics; saved projects in Supabase (F)
9. [ ] MySQL/MariaDB connector (`pymysql` + read-only session), ~30–45 min (F + H: dialect dropdown)
10. [ ] Chunked, streamed generation and export for > 500k rows (F + H)
11. [ ] Simple per-IP rate limit on `/api/generate` and the AI endpoints (F)

**Cut (do not build):** auth/RBAC, SDV training, differential-privacy claims,
MySQL/MSSQL/Mongo, GL/TB/SOCI/SOFP, Redis/Celery/Docker/CI, AI-generated rows.

---

## 9. Session Log (append one line per session, newest at the bottom)

Format: `YYYY-MM-DD HH:MM · F|H · done: … · left: … · blockers: …`

- 2026-09-29 · F · done: MVP locked, work split, CLAUDE.md rules (ownership + agent orchestration), TASKS.md, docs updated · left: F0 contract freeze · blockers: none
- 2026-09-29 · F · done: clarified DB extraction (3-step list → pick → extract, 200/1000 sample, no rows to AI), scale (1–2 AI calls/job, vectorized engine, 100k default / 500k ceiling), external DB connect + SSRF guard, no-auth access model (TTL store); updated contract, architecture, F0/F3/F5/H1, backlog · left: F0 · blockers: none
- 2026-09-29 · F · done: F0 (contract models, API contract v1.0 frozen, types.ts, in-memory store with TTL/max, all routers + stubs, CORS + `/api` prefix + error envelope, deps, .env.example, 18 tests green) + F2 templates (finance, ecommerce) + first-cut generator/validator · left: F1 AI layer, F3–F7 · blockers: none
- 2026-09-29 · F · done: F1 AI layer (AIService.generate_structured with validate → retry-with-feedback → fallback → AIProviderError; Gemini (google-genai JSON schema), Groq (httpx JSON mode), schema-aware Mock; prompts; validate.py converters), wired `/schema/from-prompt` + `/scenarios/propose` to AI; 33 tests green + 2 live tests (skipped, no key) · left: live Gemini/Groq check with real keys, F3 CSV/DB ingest, F5–F7 · blockers: no API keys in .env yet
- 2026-09-29 · F · done: F1 verified live (Gemini `gemini-2.5-flash` + Groq `openai/gpt-oss-120b` both pass `tests/test_ai_live.py`; real from-prompt returns a valid 6-table schema); fixed: provider names case-insensitive, unit tests forced to mock via `tests/conftest.py` · left: F3 ingest, F5–F7 · blockers: none (Gemini sometimes returns 503 "high demand"; Groq fallback covers it, so keep `AI_FALLBACK_PROVIDER=groq`; Groq free tier = 8k tokens/min ≈ 2 calls/min)
- 2026-09-29 · F · done: F3 ingest (CSV types/PK/FK/profiles/rules, Postgres list + extract with auto-added parents, TABLESAMPLE/random sampling, children-per-parent aggregates, SQLite upload, db_guard SSRF + read-only + error mapping, privacy-filtered AI enrichment) + F4 profiler; Manual QA rule in CLAUDE.md + `Manual Testing/backendtest1.md` with samples; 79 tests green · left: F5 engine, F6 report, F7 injection, F8 Supabase · blockers: none (Postgres path verified only against a local server's auth error; full run needs `TEST_PG_URL`)
