# Canonical Architecture (production target)

## One support-ticket execution path

```text
Support → Solve with AI
  → agent_run_service.solve
  → agent/support_graph (LangGraph supervisor → workflow → HITL → verify)
  → MCP support tools (mcp_server/support/*)
  → deterministic policy (policy_tools + approval policy)
  → HITL pause (WAITING_FOR_HUMAN, graph_state persisted on agent_runs)
  → resume SAME execution on approve/reject (decide_approval)
  → verify (eligibility re-check must flip)
  → AI_AGENT ticket message (customer sees it in their frontend)
  → RESOLVED / ESCALATED + audit trail
```

`agent/support/runner.py` (`run_ticket`) is deprecated for the ticket path
(tests only). `/api/chat` (worker tasks) never creates customer-visible
ticket messages; ticket AI always goes through the support graph.

## Canonical data model

Customer-support source of truth (Postgres `biz` schema):

- `biz.app_users` → `biz.shop_orders` → `biz.shop_order_items` → `biz.products`
- `biz.app_users` → `biz.customer_tickets` → `biz.customer_ticket_messages`
  (`CUSTOMER / AI_AGENT / SUPPORT_AGENT / SYSTEM`)
- `biz.agent_runs` (incl. `graph_state`, `workflow`, `verification_result`, `error`)
  → `biz.tool_calls` + `biz.approvals` (incl. `expires_at` 24h TTL) + `biz.audit_logs`

Legacy / sandbox tables (`biz.customers`, `biz.orders`, `biz.tickets`,
`biz.financial_*`, `biz.ops_*`, `worker.*`) serve the ops sandbox, eval
harness, and generic worker demos. They are NOT part of the customer-support
happy path. Do not build new ticket/order features on them.

## Security

- Public `/auth/register` always creates `CUSTOMER`. Staff are seeded
  (`ensure_support_admin`) — never self-elevate.
- Customer APIs (`/cart`, `/checkout`, `/orders`, `/tickets`) require JWT and
  enforce ownership by `sub`.
- Support APIs (`/support/*`) require `SUPPORT_AGENT` JWT.
- Worker plane (`/api/tasks`, `/api/chat`, `/api/approvals`, `/api/clarifications`,
  `/api/*/memory|events|evidence|verification`) requires `SUPPORT_AGENT` JWT.
- Ops sandbox login requires `SUPPORT_AGENT` JWT + staff password, then mints
  the `ops_session` cookie. Legacy `agent_name`-only login is removed.
- Direct commits (`/api/agent/direct/commits`) require `SUPPORT_AGENT` JWT
  plus the HMAC submit token; insecure default secrets are rejected outside
  `environment=local` (`assert_production_secrets` on startup).
- SSE activity accepts `Authorization: Bearer` header; `?token=` remains only
  because `EventSource` cannot set headers (single-stream scope).

## Goal-oriented agent

The supervisor classifies intent (`REFUND / REPLACEMENT / RETURN /
CANCELLATION / ORDER_STATUS / DELIVERY / PAYMENT / GENERAL_QUERY`) and picks
one workflow. Each workflow loads only its planned tools
(`agent/support_graph/planner.py`) — tracking never runs the refund chain.
Policy outcomes come from deterministic `check_*_eligibility` tools; the LLM
only drafts customer-facing text. Every mutation is verified by re-check
before the `AI_AGENT` message is written.
