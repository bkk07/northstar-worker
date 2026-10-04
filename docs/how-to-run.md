# How to run (Phase 1 skeleton — v0)

Phase 1 delivers a runnable monorepo skeleton: a FastAPI health endpoint
and a blank Vite + React frontend with `/shop`, `/ops`, `/worker`,
`/evaluation` shells. No database yet (arrives in Phase 4).

## Prerequisites

- Python 3.11+ (`python --version`)
- Node 20+ and pnpm 9+ (`node --version`, `pnpm --version`)
- `uv` (optional, recommended): https://docs.astral.sh/uv/

## 1. Configure env (no secrets committed)

```powershell
Copy-Item .env.example .env
```

`.env` is git-ignored. The committed `.env.example` documents every variable.

## 2. Backend (FastAPI, JSON-only)

```powershell
# from repo root
pip install -e ".[dev]"  # or: uv sync
uvicorn app.main:app --app-dir backend --reload --port 8000
```

Verify:

```powershell
curl http://127.0.0.1:8000/api/health
# {"status":"ok","service":"northstar-worker-backend","version":"0.1.0-phase1"}
```

Layering: `api/health_controller.py` (HTTP) → `services/health_service.py`
(logic) → `schemas/health.py` (DTO). Controllers never touch SQL.

## 3. Frontend (Vite + React + TS)

```powershell
cd frontend
npm install
npm run dev      # http://localhost:5173
```

Routes (placeholder shells in Phase 1):

- `/shop` — customer surface (Phase 7)
- `/ops` — support console the worker drives (Phase 8)
- `/worker` — Control Center (Phase 26)
- `/evaluation` — metrics dashboard (Phase 27)

Shared client lives at `src/shared/api/axiosClient.ts`; server state is
owned by TanStack Query (`src/app/providers.tsx`).

## 4. Tests

```powershell
# backend (from repo root)
pytest tests/unit tests/integration -v

# frontend (from frontend/)
npm run test       # Vitest route smoke test
npm run typecheck
```

Phase 1 tests: config loads from env, logs are single JSON lines with
secrets redacted, `GET /api/health` returns 200, frontend router exposes
the four shells.

## 5. Manual verification (Definition of Done)

1. `uvicorn` starts with no traceback; `/api/health` returns 200.
2. `npm run dev` renders the four route shells.
3. Fresh clone + `Copy-Item .env.example .env` + the two commands above
   reproduces 1–2 with no secrets committed (`git status` shows no `.env`).

## Next

Phase 2 adds Docker Postgres, ruff/mypy/import-linter gates, and
`make verify`. See `NORTHSTAR_WORKER_FINAL_PLAN.md` §29.
