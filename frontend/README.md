# Frontend

Owner: **Haider**. Status: to be scaffolded in task **H0** (see `TASKS.md`).

## Stack (locked)
React + TypeScript + Vite + Tailwind CSS + shadcn/ui ·
`@xyflow/react` (schema graph) · `@tanstack/react-table` (data previews) ·
Recharts (stretch only).

## Setup (after H0)
```powershell
cd frontend
npm install
Copy-Item .env.example .env.local   # VITE_API_URL=http://127.0.0.1:8000, VITE_USE_FIXTURES=true
npm run dev
```

## Rules
- `src/api/types.ts` is owned by Farhan (the API contract mirror). Don't edit it.
  Request changes in `TASKS.md`.
- Use fixtures mode (`VITE_USE_FIXTURES=true`) until the backend endpoint you
  need is real.
- Run `npm run build` before pushing.

Spec: `design.md`, `docs/api-contract.md`.
