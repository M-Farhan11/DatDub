# Synthetic Data Studio (HackDataV2)

A constraint-aware synthetic data studio. Give it a prompt, CSV files, a
database or a template. It understands the schema, generates a coherent
fake relational dataset with AI-proposed edge cases, proves the dataset is
valid, and exports data + invoice PDFs + ground truth.

## Start here

- **`TASKS.md`**: who does what (Farhan / Haider), status, sync protocol. Read it every session.
- `CLAUDE.md`: rules for Claude Code sessions (ownership, agent orchestration)
- `idea.md` · `architecture.md` · `design.md` · `docs/api-contract.md`: the spec
- `project-state.md` · `roadmap.md`: live status

## Repository Layout

```text
backend/      FastAPI app (Farhan; documents/ + export/ are Haider's)
frontend/     React + Vite app (Haider), scaffolded in task H0
docs/         API contract + Excalidraw diagrams
idea.md, architecture.md, design.md   Templates, filled in during Phase 1+
project-state.md, roadmap.md          Live project status
CLAUDE.md     Rules for Claude Code sessions in this repo
```

## Backend Setup (Windows / VS Code)

All commands below assume PowerShell, run from the `backend/` directory.

### 1. Create a virtual environment

```powershell
cd backend
python -m venv .venv
```

> **Note:** if your default `python` resolves to a very new release (e.g.
> 3.14) that doesn't yet have prebuilt wheels for `pydantic-core`, `pip
> install` will try to compile it from source via Rust/maturin and fail
> without an MSVC toolchain. If that happens, create the venv with a
> Python 3.11–3.13 install instead, e.g. `py -3.12 -m venv .venv`.

### 2. Activate it

```powershell
.venv\Scripts\Activate.ps1
```

(If using Git Bash instead: `source .venv/Scripts/activate`)

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

```powershell
Copy-Item .env.example .env
```

The defaults are sufficient to run locally — `AI_PROVIDER=mock` requires
no API keys. Fill in real provider keys later, once a provider is
actually selected.

### 5. Run the API

```powershell
uvicorn app.main:app --reload
```

Then visit `http://127.0.0.1:8000/api/health` — it should return
`{"status": "ok"}`. Interactive docs are at `http://127.0.0.1:8000/docs`.

### 6. Run tests

```powershell
pytest
```

No API keys or database are required to run the test suite — everything
runs against `MockProvider`.

## How environment variables work

`app/core/config.py` loads settings via `pydantic-settings` from a local
`.env` file (git-ignored) using `.env.example` as the reference template.
`AI_PROVIDER` selects the active provider by name (`mock` today);
`AI_FALLBACK_PROVIDER` is optional and used if the primary provider fails.
Provider API key variables (`GEMINI_API_KEY`, `GROQ_API_KEY`, etc.) are
present as placeholders so credentials can be dropped in quickly once a
provider is chosen — their presence does not mean those providers are
integrated yet.

## AI Mock usage

`backend/app/ai/providers/mock.py` implements `MockProvider`, which
returns deterministic, schema-valid `AIResponse` output with no external
calls. `AIService` (`backend/app/ai/service.py`) is the only class
application code should call — it resolves the configured provider by
name and falls back to a secondary provider (or raises a controlled
`AIProviderError`) if the primary fails. This lets the rest of the
application be built and tested today without any real AI credentials.

## Frontend

Deliberately not initialized. See `frontend/README.md` for why, and what
determines the eventual stack.

## What happens tomorrow, after the theme is revealed

1. The human reveals the hackathon theme and explicitly authorizes Phase 1
   in `roadmap.md`.
2. Theme analysis → idea generation → idea evaluation → select **one**
   idea → lock the MVP (fill in `idea.md`).
3. `architecture.md` and `design.md` get filled in based on the selected
   idea's actual requirements.
4. Frontend framework gets chosen based on real interaction requirements.
5. The actual AI provider(s) get selected and integrated into
   `backend/app/ai/providers/` based on the capability the product
   actually needs (text reasoning, structured output, vision, etc.).
