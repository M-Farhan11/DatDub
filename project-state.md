# Project State

> Update at the end of every session (see the sync protocol in `TASKS.md`).
> Keep it short. Detailed task status lives in `TASKS.md`.

## Current Phase

PHASE 8: IMPLEMENTATION (8-hour build). Product locked: **constraint-aware
synthetic data studio** (see `idea.md`).

## Overall

| Milestone | Status |
|---|---|
| MVP locked + work split | DONE |
| H0 contract freeze (F0) + frontend scaffold (H0) | F0 DONE · H0 TODO |
| Checkpoint 1: template → generate → preview → report | TODO |
| Checkpoint 2: DB connect, scenarios, PDF, ZIP | TODO |
| Deployed demo (Vercel + Railway + Supabase) | TODO |
| Freeze + rehearsal | TODO |

## Farhan (backend core)

- **DONE:** Phase 0 bootstrap; MVP lock; `CLAUDE.md` (ownership + agent
  orchestration rules); `TASKS.md`; `idea.md` / `architecture.md` / `design.md`;
  `docs/api-contract.md` draft v0.1
- **DONE (F0):** contract models (`backend/app/schemas/`), API contract v1.0
  frozen, `frontend/src/api/types.ts`, in-memory store (TTL 60 min, max 20,
  unguessable IDs), all 14 endpoints (real: health, templates, generate,
  table paging, invoice list; stubs: schema inference, db, scenarios),
  CORS + `/api` prefix + `{"error":{code,message}}` envelope, deps pinned.
  **F2:** finance + ecommerce templates. First-cut generator + PK/FK validator.
- **DONE (F1):** AI layer: `AIService.generate_structured` (Pydantic validation,
  one retry with error feedback, fallback provider, `AIProviderError`), Gemini /
  Groq / schema-aware Mock providers, prompts, `ai/validate.py` (drops invalid
  AI references). `/schema/from-prompt` and `/scenarios/propose` now go through AI.
- **DONE (F3 + F4):** real `from-csv`, `db/tables`, `from-db`, `from-sqlite` in
  `app/ingest/`: CSV type/semantic heuristics, PK + FK guessing (names + value
  overlap), rule inference on CSV (allowed_values, date_order, sum_of_children,
  lte_parent), profiler (null %, moments, 10-bin histogram, top values for
  non-PII low-cardinality columns, children-per-parent), Postgres/SQLite
  introspection with FK parents auto-added, sampling (TABLESAMPLE / random),
  `db_guard` (Postgres-only, query-param lockdown, SSRF guard with IP pinning via
  `hostaddr`, read-only txn + 10 s timeout, fixed error messages), privacy-filtered
  AI enrichment (heuristic fallback when AI is down). QA doc: `Manual Testing/backendtest1.md`.
- **DONE (F5):** generation engine: vectorized, seeded, profile-driven
  (histograms, category weights, date ranges), Faker value pools
  (`engine/pools.py`), children per parent from the sampled distribution or
  Poisson, child tables capped at `MAX_ROWS_PER_TABLE`, all 5 rule kinds
  enforced, null/outlier rates on non-key/non-rule columns. 5k customers < 5 s,
  100k < 30 s. QA doc: `Manual Testing/backendtest2.md`.
- **IN PROGRESS:** —
- **NEXT:** F6 validation report (types/nullability, per-rule checks, expected
  violations, similarity), F7 scenario injection + ground truth

## Haider (frontend + documents/export)

- **DONE:** —
- **IN PROGRESS:** —
- **NEXT:** H0: pull the repo, scaffold `frontend/` (Vite + React + TS +
  Tailwind + shadcn), app shell + stepper, API client with fixtures mode

## BLOCKED

- None. F0 and F3 are done; Haider can integrate against the stubs (run backend with `AI_PROVIDER=mock`).

## KNOWN ISSUES

- The system default Python is 3.14 (no `pydantic-core` wheels). Create the
  backend venv with Python 3.12: `py -3.12 -m venv .venv`.
- `google-genai` pulls pydantic 2.13 (pinned in requirements).
- Gemini free tier sometimes returns `503 UNAVAILABLE` ("high demand"). Keep
  `AI_FALLBACK_PROVIDER=groq` so calls fall through to Groq. Groq free tier is
  8k tokens/min (≈ 2 AI calls/min): fine for a demo, not for load.
- Model IDs are required in `.env` (`GEMINI_MODEL=gemini-2.5-flash`,
  `GROQ_MODEL=openai/gpt-oss-120b`); a provider without key + model is skipped (→ mock).

## Decisions log

- 2026-09-29: F5: child tables above the row cap are scaled down (not rejected), keeping each parent's minimum children while the budget allows; `GenerateResponse.notes` proposed to surface this. Faker pools use a fixed seed (cached per locale); the request seed only drives the picks, so output stays reproducible. Nulls/outliers never touch keys or rule columns, so rules stay 100% valid unless a scenario breaks them on purpose.

- 2026-09-29: F3: ingest caps `row_count_hint` at 1000; key columns become string `id`s (the engine generates keys); self-references/cycles/composite keys are dropped with a note; DB read-only + timeout are set per transaction (not as startup `options`, which Supabase's pooler rejects). New rule: one `Manual Testing/{backend,frontend}test<N>.md` per session for QA.

- 2026-09-29: Contract v1.0: generated PKs are strings (`INV-00001`); dates are `YYYY-MM-DD` strings; `date_order.via_fk` means `before` lives in the FK parent; `ForeignKey.children_distribution` added for the profiler.

- 2026-09-29: F1: AI output models are flat (`SchemaDraft`, `SemanticEnrichment`, `ScenarioPlan` in `app/ai/schemas.py`) and converted to contract models in code; Groq uses JSON mode + schema in the prompt (works on every Groq model).

- 2026-09-29: No platform DB; in-memory dataset store. Supabase is used only as
  the demo *source* DB (reachable from Railway, unlike a local DB).
- 2026-09-29: SDV/SDMetrics cut from the MVP (heavy install, slow); own
  profiler + validators instead.
- 2026-09-29: AI = Gemini primary, Groq fallback via httpx, Mock. AI
  produces plans only; rows are deterministic.
- 2026-09-29: DB flow is 3 steps: `POST /api/db/tables` (no rows) → user
  picks tables (FK parents auto-added) → extract. Sample is 200 rows/table by
  default, max 1000, profiled then discarded. Nothing raw goes to the AI.
- 2026-09-29: Scale: 1–2 AI calls per job regardless of row count;
  vectorized engine + value pools; 100k rows/table default, 500k ceiling;
  50-row previews; data delivered via ZIP.
- 2026-09-29: External DB connect: Postgres (any reachable host) + SQLite
  upload; SSRF guard; stateless credentials; MySQL in the backlog.
- 2026-09-29: No auth: open site, unguessable `dataset_id`, in-memory store
  with a 60 min TTL and max 20 datasets.
