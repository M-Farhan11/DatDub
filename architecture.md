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

## Database connection (source DB)
- Postgres URL or SQLite upload → SQLAlchemy `inspect()` → tables, columns, PK, FK
- Read-only transaction, `statement_timeout`, `LIMIT ≤ 500` per table
- Mode `schema_only` reads no rows; `schema_and_sample` reads the sample and profiles it
- The URL is never logged, stored or returned
- Demo DB: Supabase project seeded by `scripts/seed_demo_db.sql`, accessed with a read-only role

## Deployment
```text
Vercel (React) ──HTTPS──► Railway (FastAPI) ──► Gemini / Groq
                                  │
                                  └──read-only──► Supabase Postgres (demo source DB)
```
Env: `AI_PROVIDER`, `AI_FALLBACK_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`,
`GROQ_API_KEY`, `GROQ_MODEL`, `CORS_ORIGINS`, `MAX_ROWS_PER_TABLE`.

## Risks
| Risk | Mitigation |
|---|---|
| AI returns invalid JSON / is down | Structured output + retry + Groq fallback + Mock + templates |
| Supabase unreachable during the demo | Local Postgres, SQLite upload, or template fallback |
| In-memory store lost on a Railway restart | Regenerate (seeded); acceptable for the demo |
| Generation too slow | 10k rows/table cap, vectorized numpy where easy |
| Merge conflicts | File ownership in `TASKS.md`; contract frozen at H0 |
