# Northstar — Autonomous AI Support Worker

An autonomous AI support worker that takes a customer-support goal, investigates the required context, uses business tools, applies deterministic policies, requests human approval when necessary, verifies actions, and communicates the resolution directly back to the customer — operating inside a controlled ecommerce environment with real tickets, orders, products, and policies.

## Quick Links

- 🎥 [Demo Video](#demo-video)
- 🏗️ [Architecture](#architecture)
- 🚀 [Setup](#setup)
- 🧪 [Testing](#testing)
- 📄 [How This Maps to the Problem Statement](#how-this-maps-to-the-problem-statement)
- 🔒 [Security](#security)

> **GitHub Repository:** `ADD_REPOSITORY_URL`
> **Demo Video:** `ADD_VIDEO_URL` — replace the placeholder in [Demo Video](#demo-video) and `docs/demo/README.md` when your recording is ready.

---

## Demo Video

🎥 **Watch the demo:** `ADD_VIDEO_URL`

> A local demo recording can be placed at `docs/demo/demo.mp4` and will be linked from `docs/demo/README.md`. No video is committed to the repository by default.

Recommended demo to reproduce (see [Running the Demo](#running-the-demo)):

1. Customer purchases a product → order delivered → raises ticket
2. Support opens ticket → clicks **Solve with AI**
3. AI traces tool calls live → pauses for approval if required → approves → verifies → resolves
4. Customer refreshes ticket and sees the `AI_AGENT` response

---

## Customer Experience

The customer operates a real storefront — browse, add to cart, checkout with mock payment, wait ~60s for simulated delivery, then raise a free-text support ticket. The AI resolution later appears directly inside that ticket's conversation.

> Screenshots are not yet committed. Add them to `docs/screenshots/customer/` and they will appear here. See `docs/screenshots/README.md`.

- Home, product catalog, product detail, cart, checkout
- Order tracking with simulated delivery
- Support ticket creation and ticket conversation (where `AI_AGENT` messages render)

```
docs/screenshots/customer/  (add these files)
├── home.png
├── products.png
├── product-detail.png
├── cart.png
├── checkout.png
├── order-tracking.png
└── ticket.png
```

## Support Experience

The support console is a separate app with staff-only auth. Support triages a queue, inspects full customer + order context, and drives AI resolution.

> Screenshots are not yet committed. Add them to `docs/screenshots/support/` and `docs/screenshots/ai/`. See `docs/screenshots/README.md`.

- Dashboard with ticket queue (OPEN / AI_PROCESSING / WAITING_FOR_HUMAN / RESOLVED)
- Ticket detail with Customer Context + Order Context panels
- **Solve with AI** → live AI Copilot with step timeline, tool trace, and HITL approval card
- Manual fallback: reply / internal note / resolve / escalate

```
docs/screenshots/support/
├── dashboard.png
├── ticket-detail.png
├── customer-context.png
├── order-context.png
└── approval.png

docs/screenshots/ai/
├── ai-copilot.png
├── agent-progress.png
├── tool-trace.png
├── hitl.png
└── resolution.png
```

---

## Architecture

### High-Level Architecture

```mermaid
flowchart TD
    C[Customer Web :5174] --> API[FastAPI Backend :8000]
    S[Support Web :5175] --> API
    API --> DB[(PostgreSQL :5433)]
    S -->|Solve with AI| AG[agent_run_service.solve]
    AG --> LG[LangGraph — support_graph]
    LG --> MCP[MCP Support Server :8003]
    MCP --> U[User Tools\nget_user / get_user_orders / get_user_tickets]
    MCP --> O[Order Tools\nget_order / get_order_items / get_order_status / get_order_tracking]
    MCP --> P[Product Tools\nget_product / get_product_details / get_product_policy]
    MCP --> POL[Policy Tools\ncheck_refund / return / replacement / cancellation eligibility]
    MCP --> A[Action Tools\nmock_refund / mock_return / mock_replace / mock_cancel_order]
    MCP --> T[Ticket Tools\nget_ticket / add_ticket_message / resolve_ticket / escalate_ticket]
    MCP --> K[Knowledge\nsearch_knowledge]
    POL --> G[Deterministic Policy Guard]
    G --> H{Human Approval?}
    H -->|No| A
    H -->|Yes| HITL[Support Approval\nPENDING → APPROVED / REJECTED / EXPIRED]
    HITL --> LG
    A --> V[Verification\nre-check eligibility against live DB]
    V --> R[AI_AGENT Response\nticket message]
    R --> DB
    AG --> TRACE[(Trace\nagent_runs + tool_calls + approvals + audit_logs)]
    TRACE --> S

    subgraph TaskPlane [Task Plane — legacy worker tasks]
        MCP2[MCP Task Server :8002\n18 tools including browser_*]
    end
    MCP2 -.->|not used for canonical TKT- ticket solve| AG
```

Verification of diagram: `agent/support_graph` 9 nodes, `mcp_server/support` 24 tools (7 groups), `mcp_server` task plane 18 tools, policy guard is deterministic (`agent/policy` + `agent/support/approval.py`), verification re-calls eligibility, trace is `GET /support/tickets/:id/trace`.

### Autonomous Ticket Execution

```mermaid
flowchart LR
    T[Ticket] --> U[Understand\nsupervisor classifies intent + workflow]
    U --> G[Gather Context\ngoal-oriented tool plan per intent]
    G --> TL[Tools\nMCP business tools]
    TL --> O[Observe\ntool results persisted]
    O --> P[Policy\ncheck_*_eligibility]
    P --> PR[Propose\ndraft resolution + approval decision]
    PR --> A[Action\nmock_* with idempotent key]
    A --> V[Verify\nre-check eligibility]
    V --> RE[Respond\nresolution → AI_AGENT message]
    RE --> RS[Resolve\nticket RESOLVED]
```

### HITL Flow

```mermaid
flowchart TD
    AG[Agent] --> PROP[Action Proposal]
    PROP --> RISK[Risk / Policy Check\nconfidence < 0.6 or amount over cap]
    RISK --> H{Human Approval Required?}
    H -->|No| EX[Execute]
    H -->|Yes| PAUSE[Pause\npersist graph_state\ncreate Approval PENDING 24h TTL\nticket → WAITING_FOR_HUMAN]
    PAUSE --> SUP[Support Approves / Rejects\nPOST /support/approvals/ID/decision]
    SUP -->|Approved| RESUME[Resume SAME Execution\nresume_support_ticket]
    SUP -->|Rejected| REJ[Rejected\nno mutation\nAI message explains]
    SUP -->|Expired| EXP[Expired\ntakeover required]
    RESUME --> EX
    EX --> VER[Verify]
    VER --> DONE[AI_AGENT message + RESOLVED or ESCALATED]
```

### Customer → Support → AI → Customer

```mermaid
flowchart LR
    CU[Customer] --> ORD[Order]
    ORD --> DL[Delivered\n~60s simulated]
    DL --> TK[Ticket\nfree-text goal]
    TK --> SC[Support Console]
    SC --> SAI[Solve with AI]
    SAI --> WRK[AI Worker\nLangGraph + MCP]
    WRK --> RES[Resolution]
    RES --> CU
```

---

## How This Maps to the Problem Statement

| Requirement | Implementation |
|---|---|
| **Understand the goal** | `agent/support_graph/nodes.py:supervise` via `agent/support/classifier.py` → `intent` + `confidence` + `workflow` (REFUND/REPLACE/RETURN/CANCELLATION/DELIVERY/PAYMENT/GENERAL) |
| **Break task into actions** | `agent/support_graph/planner.py` goal-oriented `INTENT_TOOL_PLAN` + `graph.py` 9-node DAG (`load_ticket → supervisor → gather → check_policy → propose → human_approval → execute → verify → respond`) |
| **Use tools** | `mcp_server/support` 24 business tools (user/order/product/policy/action/ticket/knowledge) behind `mcp_server/support_server.py :8003`. No raw SQL; service-token identity. Task plane `mcp_server/server.py :8002` 18 tools includes isolated `browser_*` for legacy tasks only — not used in canonical ticket solve |
| **Observe results** | Every tool call persisted to `biz.tool_calls` with arguments + result, emitted on `bus`, rendered in `GET /trace` timeline; next node reads prior `tool_results` / `policy_context` |
| **Decide next action** | Conditional edges `_route_supervisor`, `_route_approval`, `_route_verify` branch on `approval_required`, `eligible`, `escalated` |
| **Remember relevant context** | `agent/support_graph/state.py` `SupportGraphState` (ticket/order/customer/policy/verification) persisted as `agent_runs.graph_state` JSONB — resume restores full checkpoint |
| **Detect failures** | `_fail_human`, `needs_human`/`escalated` branches, `run.status = FAILED`, ticket → `ESCALATED`; audit rows + `error` field |
| **Retry / recover** | Chat narration `TIMEOUT_S=10` draft fallback; chat runner idempotent `approval:{id}` + `agent:{ticket}:{workflow}` keys; `bus` + SSE with backfill; graph `max_steps=40` cap |
| **Verify outcome** | `nodes.verify()` re-calls `check_*_eligibility` on live DB after `execute`; `verifier/` independent snapshot-diff-invariant pipeline (`ns_verifier` read-only) never trusts the last action's OK |
| **Ask for clarification** | Worker-plane `clarification_service` parks `WAITING_FOR_CUSTOMER` with TTL; canonical graph `ask_customer` → `WAITING_FOR_CUSTOMER` + `AI_AGENT` message asking for order context |
| **Ask for approval** | `approval_policy.needs_approval` (confidence < 0.6 or refund ≥ Rs 5,000) → `Approval PENDING` 24h TTL, `waiting_for_approval` event, Resolve/Reject buttons only — typed "yes" in `chat_intent` maps to read-only `confirm` |
| **Return useful evidence** | `GET /support/tickets/:id/trace` → `agent_runs` + `tool_calls` + `approvals` + `audit_logs` + `verification_result` + `AI_AGENT` ticket message; SSE `GET /support/tickets/:id/activity` live stream |

---

## Key Product Capabilities

### Autonomous Resolution
Support provides only the high-level goal: **"Solve this ticket."** The supervisor picks a workflow, the planner loads the minimal tool set for that intent, and the graph runs without step-by-step human direction. The same path is used from both **Solve with AI** and `POST /api/chat solve ticket TKT-...` (canonical — never a worker task).

### Tool Use
All business data goes through MCP. The support plane (`:8003`, `ns_app` role, 24 tools) exposes user/order/product/policy/action/ticket/knowledge. The task plane (`:8002`, 18 tools) exposes the legacy customer/order/ticket + `browser_*` + `refund_create`/`replacement_create` for worker tasks. Both planes enforce token identity (`OPERATOR_TOKEN` / `POLICY_TOKEN_SECRET`) and both forbid raw SQL.

### Policies
Deterministic rules — not LLM-invented. `agent/policy/rules.py` + `agent/policy/eligibility.py` + `docs/policy.md` matrix (`E-REF-001`, `P-REF-001`, `E-REPL-001`, …) plus per-product `biz.policies`. The `check_*_eligibility` tools are the source of truth; the LLM only classifies.

### HITL
Two mechanisms: (1) **Approval** for risky/low-confidence actions (24h `PENDING → APPROVED/REJECTED/EXPIRED`, resume replays prefix idempotently) and (2) **Clarification** when context is missing (`WAITING_FOR_CUSTOMER`). Chat approval attempts are refused byte-exactly — "buttons only."

### Verification
Post-action, `verify` re-executes `check_*_eligibility`. If still `eligible` after a supposed mutation, the run escalates (`needs_human`) and never claims success. The standalone `verifier/` package snapshots before/after via `ns_verifier` and runs per-effect + global invariants.

### Evidence
Persisted trace (`tool_calls` with args/result, `approvals` with expiry, `audit_logs` with sequence, `agent_runs` with intent/workflow/decision/error/graph_state/verification_result), live SSE activity events, and the final `customer_ticket_messages` row (`sender_type=AI_AGENT`) the customer reads.

---

## End-to-End Example

> **"My headphones arrived damaged. I want a replacement."**

```
1. Customer (apps/customer-web :5174) signs in, ticket TKT-7F3A created as OPEN.
2. Support (apps/support-web :5175) opens /tickets/<id>.
3. Support clicks Solve with AI → POST /support/tickets/:id/solve.
4. agent_run_service.solve() creates agent_runs RUNNING, ticket → AI_PROCESSING.
5. support_graph: supervisor → REPLACEMENT / REPLACE (confidence 0.82).
6. gather loads get_ticket, get_order, get_order_items via MCP :8003.
7. check_policy calls check_replacement_eligibility → eligible, reasons [].
8. propose runs approval_policy.needs_approval(REPLACE, amount, 0.82)
   → low-confidence or over-cap? if yes → pause, else auto-execute.
9. If HITL: Approval PENDING created, WAITING_FOR_HUMAN, graph_state persisted.
   Support approves POST /support/approvals/:id/decision → resume_same_run.
10. execute calls mock_replace idempotently; verify re-calls eligibility
    → now ineligible (replacement consumed) → ok.
11. respond drafts resolution (LLM phraser with template fallback).
12. agent_run_service writes AI_AGENT message into customer_ticket_messages,
    ticket → RESOLVED, audit run_resolved emitted.
13. Support watches trace: GET /support/tickets/:id/trace (steps + approvals).
14. Customer reopens /tickets/:id on :5174 and reads the AI response.
```

---

## Customer Frontend

```
Customer Web  apps/customer-web  :5174
├── /              Home
├── /login         Login (JWT, Argon2)
├── /signup        Signup (always CUSTOMER)
├── /products      Product catalog
├── /products/:id  Product detail + policies
├── /cart          Cart (Protected)
├── /checkout      Checkout → mock payment → shop_orders
├── /orders        Order list
├── /orders/:id    Order detail + tracking
├── /support       Support tickets list
├── /tickets/new   Raise ticket (subject/body/category/priority, optional order_id)
└── /tickets/:id   Ticket detail + conversation (CUSTOMER + AI_AGENT messages)
```

Payment and delivery (~60s `DELIVERY_DELAY_SECONDS`) are simulated — the shop creates `shop_orders` and the order's status flips to DELIVERED for realistic ticket context.

## Support Frontend

```
Support Web  apps/support-web  :5175
├── /login         Staff login (SUPPORT_AGENT JWT)
├── /dashboard     Ticket queue + stats (OPEN/AI_PROCESSING/WAITING_FOR_HUMAN/RESOLVED)
├── /tickets       Queue table with filters
├── /tickets/:id   Ticket detail
│   ├── Customer Context  (get_user, user_tickets, user_orders)
│   ├── Order Context     (get_order, items, status, tracking, product policies)
│   ├── Conversation      (CUSTOMER / SUPPORT_AGENT / AI_AGENT)
│   ├── AI Copilot        (Solve with AI, trace, activity SSE, takeover)
│   ├── Approval Card     (Approve / Reject, expiry countdown)
│   └── Tool Activity     (tool_started / tool_done timeline)
└── /chat          Ticket-grounded chat
    ├── Thread history + ticket binding (TKT-XXXXXX, history → resolve_references)
    ├── Live trace for activeTicketId
    ├── Clarifications panel
    └── Approval decisions (buttons only)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Customer UI | React 18.3 + Vite 5 + TypeScript 5 + Tailwind CSS + shadcn/ui + Framer Motion |
| Support UI | React 18.3 + Vite 5 + TypeScript 5 + TanStack Query 5 + zustand + axios |
| Styling | Tailwind CSS + shadcn/ui |
| Backend | FastAPI + Pydantic + SQLAlchemy 2 + Alembic + SSE (sse-starlette) |
| Database | PostgreSQL 16 + pgvector (`:5433` host, `5432` in compose) |
| Agent | LangGraph (graph runner) + LangChain (interfaces) + hand-written `support_graph` |
| Model | Inception (`INCEPTION_API_KEY`, `mercury-2.5`, `api.inceptionlabs.ai/v1`) with Groq fallback (`llama-3.3-70b-versatile`) |
| Tools | MCP — `mcp` SDK, task plane `:8002` (18 tools), support plane `:8003` (24 tools) |
| Browser | Playwright (`browser/` + `browser_*` task-plane tools, Chromium) — isolated, not in canonical ticket path |
| Authentication | JWT (PyJWT, HS256, 24h) + Argon2 (`argon2-cffi`) + role `CUSTOMER`/`SUPPORT_AGENT` |
| Realtime | SSE — `GET /support/tickets/:id/activity` (canonical bus) + `GET /api/tasks/:id/events` (worker audit) |
| Testing | pytest + pytest-asyncio + httpx TestClient + Playwright browser tests + import-linter |
| Containerization | Docker Compose (postgres/pgvector, api, mcp, mcp-support) |
| Config | pydantic-settings (`common/northstar_common/config.py`, `env_file=.env`) |

Only technologies present in `pyproject.toml`, `apps/*/package.json`, and `docker-compose.yml` are listed.

---

## Project Structure

```
northstar-worker/
├── apps/
│   ├── customer-web/        # Customer storefront :5174
│   └── support-web/         # Support console :5175 (+ chat)
├── backend/                 # FastAPI app factory app/main.py (24 routers)
│   └── app/
│       ├── api/             # health, auth, commerce, support, agentrun, worker, ops, control
│       ├── services/        # agent_run (canonical), support, worker/*, commerce, actions
│       ├── repositories/    # thin SQLAlchemy queries (no business logic)
│       ├── core/            # auth (JWT/Argon2), deps, exceptions, security
│       └── sse/             # SSE stream + listener (worker_audit_events)
├── agent/                   # Canonical + legacy agent code
│   ├── support_graph/       # state.py, graph.py, nodes.py, planner.py, runner.py
│   ├── support/             # classifier, approval policy
│   ├── llm/                 # MercuryClient, config_from_env (Inception > Groq)
│   ├── policy/              # eligibility, authorization, issuer (HMAC)
│   ├── memory/  contract/  evidence/  runtime/  graph/  ...
│   └── llm/schemas.py       # Interpretation strict defaults
├── mcp_server/              # MCP planes
│   ├── server.py / registry.py            # :8002 task plane, 18 tools
│   └── support/  support_server.py        # :8003 support plane, 24 tools
├── database/                # SQLAlchemy models (biz + worker schemas), Alembic 0016
├── common/                  # northstar_common config + logging
├── browser/                 # Playwright perception layer (one context per run)
├── verifier/                # Snapshot-diff-invariant independent verifier (ns_verifier role)
├── eval/  frontend/  packages/            # eval scenarios, legacy shell, shared-types
├── scripts/                 # dev_up, seed, reset, seed_support_admin, browser demo, secret_scan
├── tests/                   # unit, integration, architecture, policy, recovery, verifier, browser
├── docs/
│   ├── architecture/  demo/  screenshots/  # asset structure (see below)
│   ├── how-to-run.md  canonical-architecture.md  hitl.md  policy.md  ...
│   └── mcp-tools.md
├── docker-compose.yml       # postgres :5433, api :8000, mcp :8002, mcp-support :8003
├── .env.example             # all env vars, no secrets
├── importlinter.ini         # import contracts (agent ⇄ verifier isolation)
├── pyproject.toml
└── README.md
```

Brief folder roles: `agent/support_graph` is the only ticket execution path; `mcp_server/support` is the only tool surface it uses; `backend/app/services/agent_run` is the canonical orchestrator; `database/models/biz` is source of truth, `database/models/worker` is the legacy task sandbox.

---

## Setup

### Prerequisites

- Python 3.11+ (`python --version`)
- Node 20+ (`node --version`)
- Docker + Docker Compose
- Git
- (Optional) `uv` for Python deps; Chromium via `playwright` for browser tests

### Environment

```powershell
Copy-Item .env.example .env
```

`.env` is git-ignored. `.env.example` documents every variable — never commit `.env`. Key variables:

```env
INCEPTION_API_KEY=            # primary model key; empty → draft fallback
INCEPTION_MODEL=mercury-2.5
INCEPTION_BASE_URL=https://api.inceptionlabs.ai/v1
GROQ_API_KEY=                 # fallback only when INCEPTION_API_KEY unset
JWT_SECRET=local-dev-jwt-secret-change-me-please
OPERATOR_TOKEN=local-operator-token
POLICY_TOKEN_SECRET=local-policy-secret
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/northstar
NS_APP_DATABASE_URL=postgresql+psycopg://ns_app:northstar@localhost:5433/northstar
VITE_API_URL=http://localhost:8000
SUPPORT_ADMIN_EMAIL=admin@northstar.shop
SUPPORT_ADMIN_PASSWORD=admin
```

Production boot (`assert_production_secrets` in `backend/app/main.py` and `common/northstar_common/config.py`) refuses `local-*` / `local-dev-*` secrets when `ENVIRONMENT != local`.

### Database

```powershell
docker compose up -d
docker exec northstar-postgres pg_isready -U postgres -d northstar
python -m alembic -c database/alembic.ini upgrade head   # head = 0016_support_graph_state
```

`database/alembic.ini` and `database/session.py` use `5433` on the host because a native Windows Postgres often occupies `5432`.

### Backend

```powershell
$env:PYTHONPATH='backend;common;agent;database;mcp_server;verifier;eval;browser'
python -m uvicorn app.main:app --app-dir backend --port 8000 --host 127.0.0.1
curl http://127.0.0.1:8000/api/health
# {"status":"ok","service":"northstar-worker-backend","version":"0.1.0-phase6"}
```

### MCP Servers

Support MCP is required for the canonical path; task MCP is required only for legacy worker tasks / browser.

```powershell
# Support plane :8003 (business tools, ns_app role)
$env:PYTHONPATH='backend;common;agent;database;mcp_server'
python -m mcp_server.support_server

# Task plane :8002 (legacy + browser) — separate shell
$env:PYTHONPATH='backend;common;agent;database;mcp_server'
python -m mcp_server.server
```

Both expect Postgres on `5433` and will fail fast without it.

### Customer Frontend

```powershell
cd apps/customer-web
npm install
cmd.exe /c npm run dev   # http://localhost:5174 (not 127.0.0.1 on Windows — IPv6 binding)
```

Use `cmd.exe /c npm run dev` on Windows; `Start-Process npm` fails (`%1 is not valid Win32`). Dev login: any signup creates a `CUSTOMER`; or use the seeded support identity from the Support section.

### Support Frontend

```powershell
cd apps/support-web
npm install
cmd.exe /c npm run dev   # http://localhost:5175
```

Seed the demo staff account first:

```powershell
python scripts/seed_support_admin.py  # SUPPORT_ADMIN_EMAIL / SUPPORT_ADMIN_PASSWORD from .env
```

Login at `/login` with `admin@northstar.shop` / `admin` (prefilled).

---

## Running the Demo

Reproduce the recorded demo exactly:

```text
1. Start services
   docker compose up -d
   python -m alembic -c database/alembic.ini upgrade head
   python scripts/seed_support_admin.py
   $env:PYTHONPATH='backend;common;agent;database;mcp_server;verifier;eval;browser'
   python -m uvicorn app.main:app --app-dir backend --port 8000 --host 127.0.0.1
   (separate shells) python -m mcp_server.support_server  # :8003
   cmd.exe /c npm run dev  # in apps/customer-web :5174
   cmd.exe /c npm run dev  # in apps/support-web  :5175

2. Customer app  http://localhost:5174
   - Sign up / log in
   - Browse /products → pick a product → add to cart
   - /checkout → mock payment (creates shop_orders)
   - /orders/:id shows tracking — wait ~60s → DELIVERED

3. Raise a ticket  http://localhost:5174/support
   - /tickets/new → subject/body "My headphones arrived damaged. I want a replacement."
   - category REPLACEMENT, priority NORMAL → TKT-XXXXXX created (OPEN)

4. Support app  http://localhost:5175
   - /login as admin@northstar.shop / admin
   - /dashboard sees the new OPEN ticket
   - Open /tickets/:id — Customer Context + Order Context populate

5. AI execution
   - Click Solve with AI
   - Watch AI Copilot: supernode timeline (load_ticket → supervisor → gather → check_policy → propose)
   - Tool calls stream with arguments (compact key=value detail)
   - If approval_required: card shows action_type + reason + TTL countdown

6. HITL (when shown)
   - Click Approve (or Reject to see rejection path)
   - Graph resumes SAME execution (graph_state), executes mock_replace, verifies

7. Verify resolution
   - Trace: GET /support/tickets/:id/trace shows steps + approvals + audits
   - Activity SSE: GET /support/tickets/:id/activity (history + live)

8. Customer sees result
   - Back to http://localhost:5174/tickets/:id — an AI_AGENT message with the
     resolution renders in the conversation; ticket is RESOLVED

9. Chat variant of the same canonical path
   - In Support /chat, type "Solve ticket TKT-XXXXXX" → background thread calls
     agent_run_service.solve(); ticket panel shows the same trace
   - Follow-ups "yes, look it up" resolve read-only against thread history
   - Typed "approve" is refused — buttons only
```

Routes that exist: `apps/customer-web /,/login,/signup,/products,/products/:id,/cart,/checkout,/orders,/orders/:id,/support,/tickets/:id` and `apps/support-web /login,/dashboard,/tickets,/tickets/:id,/chat`. Use `?token=` on SSE streams only (EventSource cannot send headers).

---

## Reliability

Focused prototype reliability — no distributed queues by design.

- **Retries:** `agent/llm/client.py` classifies `HTTP 429/500/502/503` + transport errors as transient and retries with backoff; chat's `_drive_with_retry` retries only transient failures, 3 attempts max, never retries 401/403/422.
- **Failure handling:** Tool timeout / browser failure / invalid state / unavailable element / API error → `_fail_human` → `needs_human` / `ESCALATED`, persisted with `error` + audit `run_escalated`. The run never claims `verified` on a failed mutation.
- **Clarification:** Free-form chat maps to `help`/`unknown` → `chat_conversation.converse` single-model call with `CHAT_LLM_TIMEOUT_S=10` draft fallback; missing-order `ask_customer` parks `WAITING_FOR_CUSTOMER`.
- **HITL:** `agent/support/approval.py` threshold (`confidence < 0.6` or amount cap) gates execution; `biz.approvals.expires_at` 24h TTL swept on every read; typed approval text is never accepted.
- **Verification:** `verify` node + `verifier/service.py` snapshot-diff-invariant both run after `execute`; `FAILED`/`BLOCKED` never renders as `verified`.
- **Idempotency:** `mock_*` use `agent:{ticket_id}:{workflow}` and `approval:{id}` idempotent keys + DB unique (`biz.shop_actions.mutation_key`, `biz.approvals`); chat dedups `PENDING_ID` ghost + `isGhost` filter.
- **Audit & trace:** `get_trace()` + `build_trace()` render idle / running / waiting / completed / failed / multi-tool states purely from persisted rows — no fake data; real timeline is the submission evidence.

---

## Important Design Decisions

### Why LangGraph?
`agent/support_graph/graph.py` encodes a stateful DAG with branching and **pause/resume** (`graph_state` JSONB checkpoint). On HITL the same execution resumes — not a restart — preserving gathered context, tool results, and policy outcome. Linear scripts cannot do this cleanly.

### Why MCP?
Two narrow planes isolate tool access: support `:8003` (business reads + policy + mock actions) and task `:8002` (legacy worker + browser). Both forbid raw SQL and share auth via `OPERATOR_TOKEN` / `POLICY_TOKEN_SECRET` + `ns_app:ns_app` role. The agent enumerates its surface in `mcp_server/support/registry.py` and `mcp_server/registry.py` parity-tested against runtime.

### Why deterministic policy?
`agent/policy/*` + `docs/policy.md` encode business rules (amount caps, replacement windows, non-refundable categories). The LLM decides intent; the tool `check_*_eligibility` decides eligibility. This prevents invented refunds/replacements and makes verification statelessly re-checkable.

### Why verification?
The last tool's `ok` is never trusted. `verify` re-queries the order's live eligibility; the `verifier/` package snapshots `customer/order/ticket + related rows` before/after through `ns_verifier` and enforces per-effect invariants (10 red-team corruptions → zero false passes). Only both passing produces `verified`.

### Why two frontends?
`apps/customer-web` and `apps/support-web` are different products with different auth (`CUSTOMER` vs `SUPPORT_AGENT`), routes, and concerns. The customer never sees approvals or traces; support never sees cart or checkout. Shared assumptions would obscure both demos.

---

## Limitations

A narrow prototype that genuinely runs — not a broad system of mocks.

- **Payment is simulated.** Checkout creates `shop_orders` with no real gateway.
- **Delivery is simulated.** `DELIVERY_DELAY_SECONDS=60` flips status server-side; no carrier.
- **Support actions are mocked** inside the app DB (`mock_refund` / `mock_replace` / `mock_return` / `mock_cancel_order` + `sg_orders`/`sg_order_items`) — correct shape for a prototype, not a payment processor.
- **Scope is controlled ecommerce.** Arbitrary third-party websites are not automated in the canonical path; browser + `api_get`/`browser_*` exist only on the legacy task plane (`:8002`) and in `tests/browser` / `scripts/browser_replacement_demo.py`.
- **Approvals have a 24h TTL.** Expired approvals require `take_over` (staff re-owns the ticket, run → `CANCELLED`).
- **Single model phrasing.** Inception `mercury` is a phraser, not an autonomous browser agent — the graph decides, the model rephrases.
- **Local single-machine.** No Kafka/Redis/Celery/K8s by design (`docker-compose.yml` non-goals header).

---

## What I Would Build Next

1. Real payment + logistics webhooks behind the current `mock_*` interface (already shaped as `amount_paise` + idempotent keys).
2. Unify `biz.tickets` (TCK-) and `biz.customer_tickets` (TKT-XXXXXX) into one canonical ticket table — the two-store split exists to avoid coupling legacy worker tasks.
3. Widen the support graph to `RETURN` / `CANCELLATION` / `DELIVERY` with richer HITL clarification (customer question thread, file upload).
4. Harden the evaluator (`eval/scenarios/catalog.yaml` S1..S40, `eval/held_out`) into CI and expose `GET /api/evaluation` quality metrics on the dashboard.
5. Richer observability: trace per-tool latency, retry counts, and verifier verdict on the support ticket page.
6. Production hardening: real operator identity, rate limits, and `pgvector` semantic search over `search_knowledge` beyond its current store.

No unnecessary heavy infrastructure is proposed for prototype scope.

---

## Testing

```powershell
$env:PYTHONPATH='backend;common;agent;database;mcp_server;verifier;eval;browser'
python -m pytest tests/unit tests/integration -q
python -m pytest tests/browser -q          # isolated Chromium on :8001/:5174 + live DB :5433
cmd.exe /c npm run typecheck               # from apps/customer-web and apps/support-web
```

The project includes unit tests (`test_chat_intent`, `test_chat_runner_retry`, `test_support_graph`, `support comprehension`, `policy` suite), integration tests (`test_chat_api`, `test_chat_canonical_solve` quarantine proving no worker task for `TKT-`, `test_canonical_solve` replacement auto + HITL resume + escalation), architecture contract tests (`test_import_contracts` vs `importlinter.ini`), browser tests, verifier red-team (10 false-success corruptions), and recovery/chaos (`test_task_cancel`, `test_faults`). Counts are not pinned in this file — run `pytest -q` to see the live tally. Do not claim a count without running it.

---

## Security

Concise and proportionate to prototype scope:

- **Authentication:** JWT (`HS256`, `JWT_SECRET`, 24h `exp`) via `backend/app/core/auth.py`; passwords are Argon2 (`argon2-cffi`).
- **Authorization:** `require_roles("SUPPORT_AGENT")` guards support APIs + `api/read|shop|catalog|worker|eval`; public `POST /auth/register` forces `CUSTOMER` (`schemas/auth.py:exclude`); staff JWT also guards `agent_run` + `direct commits`.
- **Direct commits:** JWT + HMAC (`POLICY_TOKEN_SECRET` over action params) via `mutation_tools`.
- **MCP service identity:** `require_roles_or_service` accepts `OPERATOR_TOKEN` (`local-operator-token` default) on `read_api_client` + `mutation_tools` via `context.service_token`; `assert_production_secrets()` refuses insecure defaults outside `local`.
- **Isolation:** Browser runs one Chromium context per run (`browser/`), refs are ephemeral handles; action tools (`browser_submit`, `refund_create`) are token-gated.
- **Tool permissions:** No raw SQL — reads and mutations go through service clients + registries; `biz.policies` seed truth is the only policy source.
- **Audit:** `biz.audit_logs` sequence is gapless; `biz.agent_runs.graph_state` + `verification_result` are persisted for every decision.

Prototype-risk (acceptable): single `JWT_SECRET`; local `Operator-Token`. Blocker (refused): raw SQL from MCP, approval bypass via chat text, auto-migration of `CUSTOMER` to staff.

---

## Tech Stack Detail

See [Tech Stack](#tech-stack) for the table. Version truth is `pyproject.toml` + `apps/*/package.json` + `docker-compose.yml` — listed there exactly.

---

## Project Structure Detail

See [Project Structure](#project-structure). The README does not re-list every file — ownership follows `importlinter.ini` contracts (e.g., `verifier` never imports `agent`).

---

## Documentation Asset Structure

```
docs/
├── architecture/            # (create when adding architecture PNGs)
├── demo/
│   └── README.md            # local demo video pointer (see below)
└── screenshots/
    ├── customer/            # 7 expected files (see Customer Experience)
    ├── support/             # 5 expected files
    ├── ai/                  # 5 expected files (AI + HITL)
    └── README.md            # placeholder inventory
```

No binary assets are committed by this change. Commit your screenshots/video separately — `.gitignore` does not block `docs/screenshots/**` or `docs/demo/**`, only `.env`, `node_modules/`, `dist/`, `__pycache__/`.

---

## Demo Screenshot Selection

Add these in order — most impactful first:

1. **Customer home** — `docs/screenshots/customer/home.png`
2. **Product detail (with category/price)** — `docs/screenshots/customer/product-detail.png`
3. **Order tracking (DELIVERED state)** — `docs/screenshots/customer/order-tracking.png`
4. **Customer ticket conversation (showing AI_AGENT bubble)** — `docs/screenshots/customer/ticket.png`
5. **Support dashboard queue** — `docs/screenshots/support/dashboard.png`
6. **Support ticket detail with Customer + Order context panels** — `docs/screenshots/support/ticket-detail.png`
7. **AI Copilot executing (timeline + tool calls)** — `docs/screenshots/ai/ai-copilot.png`
8. **HITL approval card (PENDING → Approve/Reject + expiry)** — `docs/screenshots/ai/hitl.png`
9. **Final resolution state (RESOLVED + AI_AGENT message visible on customer ticket)** — `docs/screenshots/ai/resolution.png`

The three README-embedded images should be one from each group: `customer/home.png`, `support/ticket-detail.png`, `ai/ai-copilot.png` (all as placeholder references until the PNGs exist).

---

## Mermaid Diagrams Included

1. High-Level Architecture (`flowchart TD`) — two frontends, FastAPI, Postgres, LangGraph, MCP support plane (7 tool groups), deterministic guard, HITL gate, verification, AI response, trace.
2. Autonomous Ticket Execution (`flowchart LR`) — Ticket → Understand → Gather → Tools → Observe → Policy → Propose → Action → Verify → Respond → Resolve.
3. HITL Flow (`flowchart TD`) — proposal → risk check → pause/resume with 24h TTL and typed-yes refusal.
4. Customer → Support → AI → Customer (`flowchart LR`) — full product loop.

All are GitHub-native Mermaid; no PNG diagrams are added.

---

## How to Verify

```powershell
# lint + import contracts + tests (what make verify runs)
ruff check .; ruff format --check .
$env:PYTHONPATH='backend;common;agent;database;mcp_server;verifier;eval;browser'
python -m pytest tests/architecture -q   # import contracts
python -m pytest tests/unit tests/integration -q
python scripts/secret_scan.py
cmd.exe /c npm run typecheck              # in apps/customer-web and apps/support-web
cmd.exe /c npm run build                  # both frontends should emit dist/ cleanly
```

---

> A user gives a support goal → the AI autonomously investigates → uses controlled tools → checks deterministic policies → handles uncertainty through HITL → executes an action → verifies the outcome → provides evidence → communicates the result to the customer.
>
> That is the story this prototype demonstrates — the ecommerce surface exists to make it realistic.

