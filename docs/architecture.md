# Architecture (draft — Phase 3)

Full version in Phase 30. This draft records the domain vocabulary and
layering rules every later phase builds on.

## Processes

| Process | Role |
|---|---|
| `backend` (FastAPI) | Commerce sandbox APIs, ops mutation APIs, worker control API, SSE |
| `runner` (Python) | Leases tasks from Postgres, executes the LangGraph |
| `mcp_server` (Python) | Typed tools, capability enforcement, Playwright host |
| `frontend` (Vite/React) | `/shop`, `/ops`, `/worker`, `/evaluation` (one app) |
| `postgres` | Source of truth (schemas `biz` and `worker`) |

## Layering

- Backend: controller (HTTP only) → service (rules) → repository (SQL) → model.
  Schemas (DTOs) cross layers; models never leave repositories.
- Agent: thin graph node → service → port → adapter/repository.
- Frontend: feature modules (`api` / `hooks` / `components` / `pages` / `types`).
- `verifier/` imports only `common` + `database.models`. `mcp_server/` has no
  DB access. Enforced by `importlinter.ini` + `tests/architecture/`.

## Domain vocabulary (`common/northstar_common/`)

- `enums.py`: `TaskState` (10), `FailureType` (14), `PolicyOutcome`
  (allow/human_approval/block), `PolicyRuleId` (E-* eligibility, P-*
  authorization), `Verdict`, `EffectType` (5, closed), `RecoveryAction`
  (11), `MemorySourceType` + `MemoryTrust`, `TicketStatus`, `TicketNoteKind`.
- `money.py`: integer paise + Indian grouping (`₹1,50,000.00`).
- `ids.py`: `mutation_key(task_id, effect_id) = sha256(task|effect)`.
- `tokens.py`: HMAC policy tokens binding (task, action, params hash).

## Task transitions (`agent/runtime/transitions.py`)

```
PENDING → RUNNING → {SUCCEEDED | FAILED | BLOCKED | INCONCLUSIVE | CANCELLED}
              ↕ WAITING_FOR_APPROVAL → (approve) RUNNING | (reject) BLOCKED
              ↕ WAITING_FOR_CLARIFICATION → (answer) RUNNING
              ↕ WAITING_ON_CUSTOMER → (reply) RUNNING | (ttl) INCONCLUSIVE
```

Terminal states have no outgoing edges; anything else raises
`InvalidTransitionError`. Phase 4 mirrors this table into
`worker.allowed_transitions` with a DB enforcement function.

## Effect registry (`agent/contract/effect_registry.py`)

Closed set of 5 effects. Each entry carries the capability checked by the
MCP server, the `/ops` form flow, the expected-state schema validated by
the contract compiler, the governing policy rules, and the verifier
invariant that proves it. Adding a workflow = adding a registry entry
(Phase 28 asserts core graph/tool code stays untouched).

## Trust boundaries

Untrusted (customer/ticket/page text) → semi-trusted (LLM proposals) →
trusted core (contract compiler, validator, policy, classifier, router,
verifier). Only `browser_submit` with a valid HMAC policy token commits,
and only through the `/ops` UI. The verifier reads DB state with its own
role and imports nothing from the agent.

## Schema reference (Phase 4)

PostgreSQL 16, schemas `biz` (commerce) and `worker` (operations).
All PKs are UUID, timestamps `timestamptz`, money integer paise, human
codes (`C102`, `ORD-1942`, `TCK-101`) UNIQUE. Migrations:
`database/alembic/versions/0001_biz.py`, `0002_worker.py` (both reversible).

### `biz` tables

| Table | Guards |
|---|---|
| customers | UNIQUE code/email; trigram GIN on `lower(name)` (look-alikes) |
| orders | UNIQUE code; CHECK paid ≤ total |
| order_items | CHECK qty > 0 |
| tickets | UNIQUE code; indexes on status, customer |
| ticket_notes | UNIQUE mutation_key (nullable) |
| refunds | UNIQUE mutation_key; CHECK amount > 0; partial UNIQUE (ticket, order) while not cancelled; trigger rejects totals above paid |
| replacements | UNIQUE mutation_key; partial UNIQUE (order_item) while pending/shipped |
| policies | UNIQUE rule_key (engine thresholds) |
| mutation_log | UNIQUE mutation_key, written atomically with each mutation |
| ops_sessions | session-expiry fault target |
| fault_plans | armed/consumed chaos faults (control plane only) |

### `worker` tables

tasks (+status index), task_runs (UNIQUE task/attempt, lease columns),
task_checkpoints (UNIQUE run/seq), task_contracts, actions (UNIQUE
run/seq, UNIQUE mutation_key), action_attempts (UNIQUE action/no),
policy_decisions, approvals, clarifications, audit_events (bigserial
seq, append-only), memory_items (trust field), snapshots,
verification_results, evidence, allowed_transitions.

`tasks.status` changes are rejected by trigger
`trg_tasks_transition` unless the pair is in `allowed_transitions`
(seeded from `agent/runtime/transitions.py`; a test keeps them in sync).

### Roles (least privilege, default-deny)

| Role | May |
|---|---|
| `ns_app` | Write `biz.*`; API-owned `worker.*`; audit INSERT/SELECT only |
| `ns_runner` | Write `worker.*`; read `biz` via `worker.v_*` views only |
| `ns_verifier` | SELECT-only everywhere |
| `ns_test_redteam` | Test-only writer of bad states (red-team) |

`audit_events` denies UPDATE/DELETE to every worker role. Local role
passwords are dev parity only; per-role engines in `database/session.py`
(`DATABASE_URL` / `NS_*_DATABASE_URL`). Host port is **5433**: a native
Windows PostgreSQL often occupies 5432.

## Agent graph (Phase 12)

Typed `WorkerState` (`agent/graph/state.py`) flows through 15 thin nodes
(`agent/nodes/`); pure functions in `agent/graph/edges.py` route every
conditional edge and fail closed on unknown values. `builder.py`
compiles this topology (stub bodies; services attach in Phases 13-24):

```
understand -> contract -> {plan | clarification(park) | finalize}
plan -> decide -> validate -> {decide(retry) | policy_check | finalize}
policy_check -> {execute | human_approval(park) | finalize}
execute -> observe -> {decide | verify | classify}
classify -> recover -> {observe | execute | probe_reconcile | plan |
                        human_approval | clarification | finalize}
probe_reconcile -> {observe | execute | finalize}
verify -> {finalize | recover}
clarification(answered) -> contract
finalize -> END
```

Checkpoints (`agent/repositories/checkpoint_repository.py`,
`agent/graph/checkpointer.py`) persist one row per node transition
(`worker.task_checkpoints`); the journal stays authoritative and the
LangGraph state is a cache. Nodes import services only — never
repositories, adapters, or LLM clients (gated).

## Mercury client (Phase 12)

`agent/llm/client.py` proposes typed objects (`schemas.py`:
`Interpretation`, `PlanProposal`, `NextAction`, `SummaryDraft`) over the
OpenAI-compatible Inception endpoint at temperature 0 with a strict
JSON-schema response format, bounded malformed-JSON retries, then raises.
Prompts live in `agent/llm/prompts/`; ports in `agent/ports/`
(`ToolGateway`, `VerifierPort`, `ClockPort`).
