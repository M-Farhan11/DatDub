# Architecture

Status: **LOCKED for MVP** (2026-09-29). Changes require human approval.

## Architecture Principles
- Simplest architecture that satisfies the MVP
- Deterministic code for deterministic problems (generation, validation, arithmetic)
- AI only for semantics, planning and scenario proposals, always as structured, validated output
- Provider-neutral AI integration (`AIService`)
- One internal contract (`DatasetSchema`) shared by every stage
- Optimize for hackathon reliability and demoability

## Stack
| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, pandas, NumPy, Faker |
| DB introspection | SQLAlchemy `inspect()` + psycopg (Postgres), built-in sqlite |
| Documents | ReportLab |
| AI | `AIService` → GeminiProvider (google-genai) / GroqProvider (httpx) / MockProvider |
| Frontend | React + TS + Vite + Tailwind + shadcn/ui, @xyflow/react, @tanstack/react-table |
| Hosting | Vercel (FE), Railway (BE), Supabase Postgres (**demo source DB only**) |
| Platform storage | In-memory dataset store (`engine/store.py`). No platform DB. |

**Not used in MVP:** SDV/SDMetrics (heavy torch install, slow training;
replaced by our own profiler + validators), Docker, Redis, auth.

## Pipeline

```text
 INPUT                         SCHEMA INTELLIGENCE            USER REVIEW
 prompt ──(AI)──┐              types · PK/FK · semantic       React Flow graph
 CSV files ─────┼──► ingest ──► PII · confidence · rules ───► + field inspector
 Postgres/SQLite┤   (+profile)          │                     (edit semantic/PII)
 template ──────┘                       ▼                            │
                                  DatasetSchema ◄────────────────────┘
                                        │
             ┌──────────────────────────┼────────────────────────┐
             ▼                          ▼                        ▼
      generation config          rules (catalogue)     scenarios (AI proposes
      rows·seed·null·outlier                            from catalogue, user picks)
             └──────────────────────────┼────────────────────────┘
                                        ▼
                        GENERATION ENGINE (deterministic, seeded)
                 topological FK order → Faker/profile sampling →
                 cardinality → rule enforcement → null/outlier → scenario injection
                                        ▼
                        VALIDATION: PK · FK · types · rules (injected = expected)
                                    · similarity vs profile
                                        ▼
                   dataset store ──► preview · report · ground truth
                                        ├──► invoice PDF (documents/)
                                        └──► ZIP export (export/)
```

## Backend module layout
```text
backend/app/
  ai/          service.py, base.py, prompts.py, providers/{mock,gemini,groq}.py   [F]
  schemas/     contract Pydantic models                                           [F]
  ingest/      csv.py, prompt.py, database.py, profiler.py, heuristics.py         [F]
  templates/   ecommerce.py, finance.py                                           [F]
  engine/      generator.py, rules.py, store.py                                   [F]
  scenarios/   catalogue.py, injector.py                                          [F]
  validation/  checks.py, similarity.py                                           [F]
  documents/   invoice_pdf.py                                                     [H]
  export/      zip_export.py                                                      [H]
  api/         one router per area (documents.py, export.py = H; others = F)
```

## Domain Model: `DatasetSchema`
`DatasetSchema { name, source, tables[], rules[], document_hints }`
`TableSchema { name, primary_key, columns[], foreign_keys[], row_count_hint }`
`ColumnSchema { name, data_type, semantic_type, nullable, unique, pii, confidence, allowed_values, min, max, profile? }`
`ForeignKey { column, ref_table, ref_column, cardinality, min_children, max_children }`
The full JSON is in `docs/api-contract.md`.

## Rule catalogue (deterministic)
`range`, `allowed_values`, `date_order`, `sum_of_children`, `lte_parent`.
The engine **enforces** them during generation and the validator **checks**
them afterwards.

## Scenario catalogue (deterministic injection)
| kind | effect |
|---|---|
| `null_burst` | N rows get NULL in a nullable column |
| `extreme_value` | N rows get values far outside the normal range |
| `duplicate_record` | N rows are duplicated with new PKs (e.g. duplicate payment) |
| `boundary_date` | N rows at date boundaries (month end, leap day, far past/future) |
| `rule_violation` | N rows deliberately break a named rule (e.g. payment > invoice) |

Each injection writes a `GroundTruthEntry` (affected IDs + expected
behaviour). The validator counts those violations as *expected*.

## AI Workflow
| Call | Input sent to the LLM | Output model |
|---|---|---|
| Prompt → schema | user prompt | `SchemaDraft` (tables, columns, FKs, rules from the catalogue) |
| Semantic enrichment | column names, dtypes, aggregate stats, low-card non-PII categories | `SemanticEnrichment` (semantic_type, pii, confidence per column) |
| Scenario proposals | schema (no rows) + user instruction | `ScenarioPlan` (proposals from the catalogue) |

Flow: `AIService.generate_structured()` → Pydantic validation → one retry →
fallback provider → `AIProviderError`. The caller then validates references
against the schema and drops invalid items. `MockProvider` returns canned
valid objects so everything works offline.

**Privacy stance (what we claim):** raw source rows are never sent to an
external LLM; the source DB is read-only and only a small sample is read;
output is newly generated values, not copies. We do **not** claim
differential privacy.

**AI call budget:** 1–2 calls per job regardless of row count (schema
understanding + scenario proposals). The output is a plan of a few KB, and
the engine produces every row. 500 rows and 500,000 rows cost the same
number of AI calls.

## Database connection (source DB)

**Supported:** Postgres (Supabase, Neon, RDS, Railway PG, …) via a URL or
separate fields, and SQLite via file upload. MySQL is in the backlog.
SQL Server/Oracle are out of scope.

**Three-step flow (the user controls each step):**
1. **List tables** (`POST /api/db/tables`): table names, column counts,
   `estimated_rows` from `pg_class.reltuples`, FK references. **No rows read.**
2. **Select:** the user ticks tables. FK parent tables are auto-added so the
   relations stay valid. Mode `schema_only` (no rows) or `schema_and_sample`.
3. **Extract** (`POST /api/schema/from-db`): SQLAlchemy `inspect()` gives
   columns, types, PK, FK, nullability, unique. In sample mode:
   - read `sample_limit` rows per table (default 200, max 1000): `TABLESAMPLE SYSTEM` for large tables, `ORDER BY random() LIMIT n` for small ones;
   - profile the rows in memory;
   - **discard the raw rows**.

**What reaches the AI:** table/column names, types, constraints and
aggregate stats. Category values only for columns with < 20 distinct values
that are not PII. PII values (names, emails, phones, addresses) are never
sent and never copied into the output; Faker regenerates them.

**Safety (outside users can connect their own DB):**
- Only `postgresql://` / `postgres://` URLs are accepted (plus SQLite upload).
- **SSRF guard:** resolve the host and reject loopback, private (10/8, 172.16/12, 192.168/16), link-local (169.254/16, cloud metadata) and IPv6 equivalents when `ALLOW_PRIVATE_DB_HOSTS=false`. Set it to `true` only for local dev.
- `connect_timeout=5`, read-only transaction (`SET TRANSACTION READ ONLY`), `statement_timeout=10s`, a `LIMIT` on every query.
- **Stateless connection:** no connection or credential survives the request.
  - The frontend keeps the credentials in memory only and re-sends them for each call.
  - They are never logged (redacted from errors), stored or echoed back.
- The UI recommends a read-only DB user and shows the SQL to create one.
- A DB on someone's own laptop (`localhost`) is not reachable from the
  deployed backend. The user runs our backend locally or exposes the DB with a
  tunnel (ngrok / Cloudflare Tunnel). The UI states this.

**Demo DB:** a Supabase project seeded by `scripts/seed_demo_db.sql`, accessed with a read-only role.

## Generation at scale
- **Limits:** `MAX_ROWS_PER_TABLE` = 100,000 by default, with a hard ceiling of 500,000. The UI warns on "large jobs".
- **Vectorized:** NumPy generates numerics, dates and categoricals a whole column at a time.
- **Pools instead of per-row Faker:**
  - pre-generate ~5,000 first names, last names, streets, companies, etc. with a seeded Faker;
  - combine them with vectorized random indices;
  - build emails from name + sequence number so they stay unique.
- **FKs:** child FK columns sample parent PKs that were already generated, so integrity is 100% by construction.
- **Delivery:** the UI only receives 50 preview rows per table. The full data comes from paged reads and the ZIP.
- **Memory:** about 100–200 MB for 500k rows × 10 columns.
- **Beyond 500k:** chunked, streamed export is in the backlog.

## Access model (no accounts)
Open website, no login/register.
- Each dataset gets a random, unguessable `dataset_id`.
- The in-memory store keeps datasets for `DATASET_TTL_MINUTES` (60), at most `MAX_DATASETS` (20), and evicts the oldest first.
- Quota protection: the row caps, 1–2 AI calls per job and the Groq/Mock fallback.
- A per-IP rate limit is in the backlog.

## Deployment
```text
Vercel (React) ──HTTPS──► Railway (FastAPI) ──► Gemini / Groq
                                  │
                                  └──read-only──► Supabase Postgres (demo source DB)
```
Env: `AI_PROVIDER`, `AI_FALLBACK_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`,
`GROQ_API_KEY`, `GROQ_MODEL`, `CORS_ORIGINS`, `MAX_ROWS_PER_TABLE` (100000),
`MAX_DATASETS` (20), `DATASET_TTL_MINUTES` (60), `ALLOW_PRIVATE_DB_HOSTS`
(false when deployed, true locally), `DEFAULT_SAMPLE_LIMIT` (200), `MAX_SAMPLE_LIMIT` (1000).

## Risks
| Risk | Mitigation |
|---|---|
| AI returns invalid JSON / is down | Structured output + retry + Groq fallback + Mock + templates |
| Supabase unreachable during the demo | Local Postgres, SQLite upload, or template fallback |
| In-memory store lost on a Railway restart | Regenerate (seeded); acceptable for the demo |
| Generation too slow / out of memory | 100k default cap (500k ceiling), vectorized NumPy, value pools instead of per-row Faker |
| Public DB-connect feature abused (SSRF) | Postgres-only, private-IP block, timeouts, read-only, no stored credentials |
| Strangers burn the AI quota | 1–2 AI calls per job, row caps; per-IP rate limit in the backlog |
| Merge conflicts | File ownership in `TASKS.md`; contract frozen at H0 |
