# CLAUDE.md

Project rules for Claude Code sessions working in this repository.

## Role

Claude Code is the primary implementation agent. The humans make final
decisions. GPT may separately review Claude's work (architecture review,
code review, debugging, technical reasoning) but does not independently
own implementation.

Team:

- **Farhan (F)**: backend lead (backend core, AI, engine, validation)
- **Haider (H)**: frontend lead (all of `frontend/`) plus two isolated
  backend modules (documents/PDF and ZIP export)
- 3rd member: presentation (not tracked in this repo)

## START OF EVERY SESSION: READ FIRST

1. `git pull --rebase`
2. Read `TASKS.md`: who owns what, what is done, what is next, open Requests
3. Read `docs/api-contract.md` if touching anything that crosses the
   frontend/backend boundary
4. If it is not obvious which person you are working for (Farhan or
   Haider), ask the human. Then work ONLY on that person's tasks and files.

## Project Goal

Build the strongest working AI hackathon solution possible within 8 hours.

## Product (LOCKED: do not redesign)

**Theme:** Synthetic Data Platform (HackDataV2, see the PDF in the repo root).

**Product:** Constraint-aware synthetic data studio.
Source (prompt / CSV / database / template) → AI understands the schema →
user reviews the schema graph → configure + choose AI-proposed edge-case
scenarios → deterministic generation → validation report → ground truth →
export (CSV / JSON / invoice PDF / ZIP).

Full spec: `idea.md`, `architecture.md`, `design.md`, `docs/api-contract.md`.
Task list and ownership: `TASKS.md`.

**Stack (locked):**

- Backend: Python 3.12, FastAPI, Pydantic v2, pandas, NumPy, Faker,
  SQLAlchemy (introspection only) + psycopg, ReportLab, google-genai
- Frontend: React + TypeScript + Vite + Tailwind + shadcn/ui,
  React Flow (`@xyflow/react`), TanStack Table, Recharts (stretch only)
- AI: `AIService` → Gemini (primary) / Groq via httpx (fallback) / Mock
- Deploy: Vercel (frontend), Railway (backend), and Supabase Postgres as
  the **demo source database only**. The platform itself has NO database.
  Generated datasets live in an in-memory store.

**Still forbidden (unless the humans explicitly approve):**

- authentication, RBAC, user accounts
- a platform/application database, migrations, persistence of projects
- Redis, queues, Celery, microservices, Docker, CI/CD, Nginx, caching
- SDV / SDMetrics / any model training (stretch only, after MVP is green)
- AI SDKs other than `google-genai` (Groq uses plain `httpx`)
- MySQL / MSSQL / MongoDB / Oracle connectors
- accounting statements (GL, TB, SOCI, SOFP)
- AI generating data rows (AI produces plans; code produces rows)
- claiming "differential privacy" or "100% privacy guaranteed"

## Phase Lock Rule

Do NOT start any roadmap phase marked `Status: LOCKED` in `roadmap.md`
unless a human explicitly authorizes it.

## Scope Rule

Before adding a dependency or architectural component, ask:

```text
Does the current requirement need this?
```

If no: do not add it. MUST-HAVE tasks in `TASKS.md` come before anything
in the Enhancements backlog.

## Team Ownership & Sync Rule

The two developers work in parallel on one repo. File ownership prevents
merge conflicts.

- **Edit only files owned by the person you are working for** (see the
  ownership table in `TASKS.md`).
- If you need a change in the other person's file, a new backend
  dependency, or a change to `docs/api-contract.md`, do NOT make it. Add
  an entry under **Requests** in `TASKS.md` and tell the human.
- Farhan owns the API contract (`docs/api-contract.md`,
  `backend/app/schemas/`, `frontend/src/api/types.ts`). Changing it
  requires both humans to agree.
- Run `git pull --rebase` before starting work and again before pushing.
- Make small, coherent commits. Prefix commit messages with `[F]` or `[H]`.
- Never push a broken `main`. Before pushing, run `pytest` (backend) or
  `npm run build` (frontend).

**At the end of every session (mandatory):**

1. Update the status of your tasks in `TASKS.md`
   (`[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked).
2. Add one dated line to the **Session Log** in `TASKS.md`: who, what got
   done, what is left, any blocker.
3. Update `project-state.md` (DONE / IN PROGRESS / NEXT for your person).
4. Commit and push those doc updates together with the code.

Only mark a task `[x]` after it has been run and meets its acceptance
criteria.

## Agent Orchestration Rule

### Primary Principle

Use the strongest available model for architectural reasoning and complex
coordination. Delegate well-defined implementation tasks to cheaper/faster
models when appropriate.

### Architect / Lead: Opus

Opus acts as the primary architectural and orchestration model.

Use Opus for:

- Understanding the overall task and requirements
- Making architectural decisions
- Designing system boundaries
- Breaking complex work into independent tasks
- Deciding which tasks should be delegated
- Reviewing important implementation decisions
- Resolving ambiguity between components
- Coordinating integration between subagents
- Reviewing the final result of complex work

Do NOT use Opus for trivial implementation work that a smaller model can
complete reliably.

### Implementation Subagents: Sonnet

Use Sonnet as the default implementation subagent for well-defined tasks.

Suitable tasks include:

- Individual API endpoints
- Pydantic schemas
- Database models
- CRUD services
- Frontend components
- Styling
- Tests
- Documentation
- Small refactors
- Boilerplate
- Clearly specified integrations

Each subagent should receive a bounded task with:

1. Context
2. Exact objective
3. Relevant files
4. Constraints
5. Acceptance criteria
6. Expected output

### Delegation Rules

Do NOT delegate a task merely to use a subagent.

Delegate when:

- The task is sufficiently self-contained.
- The implementation can be specified clearly.
- The subagent can work without repeatedly asking for architectural
  decisions.
- Delegation is likely to reduce expensive reasoning/context usage.
- Multiple independent tasks can be worked on in parallel.

Keep work in the primary Opus context when:

- Requirements are ambiguous.
- Architecture is still being decided.
- Several components are tightly coupled.
- The task requires substantial reasoning across the whole codebase.
- Integration decisions are involved.
- A subagent would need extensive context before it could work
  effectively.

### Parallelism

Independent tasks may be delegated to separate subagents.

```text
Opus
 │
 ├── Sonnet → Backend API
 ├── Sonnet → Frontend component
 └── Sonnet → Tests
```

Do NOT parallelize tasks that modify the same files or depend heavily on
each other's unfinished work.

### Integration

Subagents must not independently redesign the architecture. Opus remains
responsible for keeping the architecture consistent.

After delegated work completes:

1. Review the changes.
2. Run tests.
3. Resolve conflicts.
4. Integrate the work.
5. Update `project-state.md` and `TASKS.md`.

### Token Efficiency

The goal is not simply to spend as few tokens as possible. The goal is to
maximize:

```text
Useful engineering output
        /
Total model cost + context consumption + coordination overhead
```

Avoid:

- Repeatedly giving the same context to multiple agents
- Delegating trivial tasks
- Spawning agents for tasks that take only a few edits
- Having multiple agents independently solve the same problem
- Asking agents to rediscover architecture already documented in
  CLAUDE.md
- Re-running expensive architectural analysis unnecessarily

Prefer:

```text
Opus:   Understand → Design → Decompose
Sonnet: Implement bounded tasks
Opus:   Review → Integrate → Resolve
```

### Human Authority

The human developers remain the final decision-makers.

Agents may propose architectural changes. They must not silently redesign
the system because they believe another approach is better.

When a task conflicts with documented architecture, stop and raise the
conflict instead of silently changing the architecture.

## Coding Agent Task Pattern

For major tasks, follow:

```text
CONTEXT
TASK
INPUT CONTRACT
OUTPUT CONTRACT
CONSTRAINTS
FILES THAT MAY BE MODIFIED
ACCEPTANCE CRITERIA
TEST REQUIREMENTS
```

After each substantial task, report:

```text
Files changed
Tests executed
Problems encountered
Remaining work
```

## AI Rules

- Application logic must not depend directly on a provider SDK. Go
  through `AIService` (`backend/app/ai/service.py`).
- AI returns **structured output** (Pydantic models), never free text that
  code then parses ad hoc.
- Validate every model response against the schema. Drop invalid items
  (e.g. a scenario that references a column that does not exist).
- AI may only choose from the fixed **rule catalogue** and **scenario
  catalogue** (see `architecture.md`). The deterministic engine executes
  them.
- **Never send raw data rows to the LLM.** Send only column names, types
  and aggregate statistics. Send category values only for low-cardinality
  columns that are not PII.
- Do not use AI for arithmetic, validation, thresholds, or row generation.
- Keep the provider abstraction thin (`AIProvider` → `AIService` →
  providers). No factories, registries, plugin systems, or DI frameworks.
- Model IDs come from `.env`. Never hard-code them.
- `MockProvider` must stay usable: no external calls, no API key, and
  valid canned objects for every structured model, so the full demo works
  offline.

## Security Rules

- Never log, store, or return in responses the database connection
  strings that users supply.
- Open source databases **read-only** (read-only transaction + statement
  timeout + row `LIMIT`). Never write to a source database.

## Git / Change Rules

- Do not commit secrets. Keep `.env` ignored.
- Avoid unrelated changes. Do not rewrite files unnecessarily.
- Prefer small coherent changes.
- Run relevant tests before reporting completion.
