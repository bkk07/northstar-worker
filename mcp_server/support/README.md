# Support MCP server (Phase 7)

Business capabilities as MCP tools for the Phase 8 support agent — separate
from the task/browser plane (`mcp_server/server.py`, :8002).

## Tool groups (24 tools, see `support/registry.py`)

USER (`get_user`, `get_user_orders`, `get_user_tickets`) · ORDER
(`get_order`, `get_order_items`, `get_order_status`, `get_order_tracking`) ·
PRODUCT (`get_product`, `get_product_details`, `get_product_policy`) ·
POLICY (`check_*_eligibility`) · ACTIONS (`mock_refund`, `mock_return`,
`mock_replace`, `mock_cancel_order`) · TICKET (`get_ticket`,
`add_ticket_message`, `update_ticket`, `resolve_ticket`, `escalate_ticket`) ·
KNOWLEDGE (`search_knowledge`).

Tools call the backend service layer with short-lived `ns_app` sessions —
no raw SQL, uniform `{ok, ...}` / `{ok: False, code, error}` envelopes.
Action tools are idempotent by caller-chosen `mutation_key`.

## Run

```bash
PYTHONPATH=common;backend;database python -m mcp_server.support_server
# SSE on SUPPORT_MCP_PORT (default 8003)
```

Or via compose: `docker compose up mcp-support` (needs migrations applied;
uses `NS_APP_DATABASE_URL`).

## Inspect

```bash
npx @modelcontextprotocol/inspector --cli http://127.0.0.1:8003/sse --method tools/list
```
