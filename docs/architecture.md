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
