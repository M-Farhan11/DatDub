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
| H0 contract freeze (F0) + frontend scaffold (H0) | TODO |
| Checkpoint 1: template → generate → preview → report | TODO |
| Checkpoint 2: DB connect, scenarios, PDF, ZIP | TODO |
| Deployed demo (Vercel + Railway + Supabase) | TODO |
| Freeze + rehearsal | TODO |

## Farhan (backend core)

- **DONE:** Phase 0 bootstrap; MVP lock; `CLAUDE.md` (ownership + agent
  orchestration rules); `TASKS.md`; `idea.md` / `architecture.md` / `design.md`;
  `docs/api-contract.md` draft v0.1
- **IN PROGRESS:** —
- **NEXT:** F0: git init + push, contract models, `types.ts`, stub routers,
  dataset store, deps

## Haider (frontend + documents/export)

- **DONE:** —
- **IN PROGRESS:** —
- **NEXT:** H0: pull the repo, scaffold `frontend/` (Vite + React + TS +
  Tailwind + shadcn), app shell + stepper, API client with fixtures mode

## BLOCKED

- Haider's real API integration is blocked until F0 is pushed. Use fixtures mode meanwhile.

## KNOWN ISSUES

- The system default Python is 3.14 (no `pydantic-core` wheels). Create the
  backend venv with Python 3.12: `py -3.12 -m venv .venv`.
- Git is initialized locally (`main`, first commit). No remote yet, so push is still pending.

## Decisions log

- 2026-09-29: No platform DB; in-memory dataset store. Supabase is used only as
  the demo *source* DB (reachable from Railway, unlike a local DB).
- 2026-09-29: SDV/SDMetrics cut from the MVP (heavy install, slow); own
  profiler + validators instead.
- 2026-09-29: AI = Gemini primary, Groq fallback via httpx, Mock. AI
  produces plans only; rows are deterministic.
