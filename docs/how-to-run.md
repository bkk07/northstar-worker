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

---

# Phase 2: quality gates and local infrastructure (v1)

## 1. Infrastructure

```powershell
# starts Postgres 16 (empty `northstar` DB; schemas arrive in Phase 4)
docker compose up -d
docker exec northstar-postgres pg_isready -U postgres -d northstar
```

Or via make (Unix): `make up`. Scripts: `scripts/dev_up.sh`,
`scripts/install_browsers.sh` (Chromium for the Phase 10 browser layer).

> `.env` must be canonical `KEY=value` lines (no quotes/semicolons) —
> docker compose parses it strictly, unlike most app loaders.

## 2. Gates (`make verify` = `make lint` + `make test`)

| Gate | Command (Windows / no `make`) |
|---|---|
| ruff lint + format | `ruff check .`, `ruff format --check .` |
| mypy (strict on `common`, `verifier`) | `python -m mypy common/northstar_common verifier` |
| import contracts (§8) | `$env:PYTHONPATH='.;backend;common'; lint-imports --config importlinter.ini` |
| architecture tests | `python -m pytest tests/architecture -q` |
| backend tests | `python -m pytest -q` |
| frontend lint/type/test | `npm run lint`, `npm run typecheck`, `npm run test` (from `frontend/`) |

Layer rules live in `importlinter.ini` and are enforced identically by
`tests/architecture/test_import_contracts.py`. Adding a forbidden import
(e.g. `agent` inside `verifier/`) fails both. The `eval.oracle_rules`
contract enables in Phase 5 when that file is created.

## 3. Pre-commit (optional)

```powershell
pip install pre-commit; pre-commit install
```

---

# Phase 5: seed data (v1)

```powershell
# reproducible world: 14 customers, 33 orders, 45 tickets, 14 policies
.\scripts\seed.sh      # or: make seed (Unix) — prints the world hash
.\scripts\reset.sh     # or: make reset — truncates biz + worker
```

`reset && seed` reproduces an identical world hash. Scenario catalogue:
`eval/scenarios/catalog.yaml` (S1..S40; S901+ reserved for held-out).

---

# Phase 7: shop frontend (v1)

```powershell
cd frontend
npm run generate:types  # regenerate DTOs from a running backend (:8000)
npm run test:e2e         # Playwright: raise a ticket, confirm the DB row
```

Shop DTOs are generated (`src/shared/types/dto.ts`, committed) — feature
code aliases them, never re-declares them.

---

# Phase 8: ops console (v1)

```powershell
cd frontend
npm run test:e2e -- e2e/ops.spec.ts  # login, queue, forms, idempotency, 401
```

`/ops` consumes the session-cookie API with per-form idempotency keys;
a 401 anywhere returns to `/ops/login`. UI flags come from
`GET /api/ops/ui-flags` (armed fault plans, Phase 9).

---

# Phase 9: control plane (v1)

```powershell
$op = @{ Authorization = "Bearer local-operator-token" }
# arm a fault, then clear it
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/control/chaos -Method POST `
  -Headers $op -ContentType "application/json" `
  -Body '{"fault_type":"TIMEOUT","target":"ops.notes",
    "trigger":{"nth_call":1},"params":{"delay_seconds":2}}'
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/control/reset -Method POST -Headers $op
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/control/seed -Method POST -Headers $op
```

Fault catalogue: `docs/evaluation.md` (draft). Never expose the operator
token to the browser bundle or the worker.

---

# Phase 10: browser layer (v1)

```powershell
python -m playwright install chromium  # or ./scripts/install_browsers.sh
python -m pytest tests/browser -q      # isolated servers on :8001/:5174
# headed replacement demo (backend :8000 + vite :5173 up, fresh seed):
python scripts/browser_replacement_demo.py
```

One Chromium context per run (`browser/`); refs are ephemeral
accessibility handles, never selectors. Perception notes:
`browser/README.md`.
