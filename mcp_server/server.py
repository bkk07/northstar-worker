"""MCP server: the typed tool boundary (plan §11, §14).

SSE transport (`MCP_PORT`, default 8002) for the agent + a localhost-only
admin route that registers task capabilities (no tool can self-grant).
The server holds no DB credentials: reads go through GET-only HTTP,
writes go only through the hosted browser.

Manual check with the MCP inspector:
  npx @modelcontextprotocol/inspector --cli http://127.0.0.1:8002/sse --method tools/list
"""

import os

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_server import context
from mcp_server.tools.browser import act_tools, session_tools
from mcp_server.tools.read import customer_order_tools, ticket_policy_tools
from mcp_server.tools.state import probe_tools

mcp = FastMCP(
    "northstar-tools",
    host="127.0.0.1",
    port=int(os.environ.get("MCP_PORT", "8002")),
)


@mcp.custom_route("/admin/tasks/{task_id}/capabilities", methods=["POST"])
async def grant_capabilities(request: Request) -> JSONResponse:
    """Register a task's capabilities (localhost admin channel, not a tool)."""
    client = request.client.host if request.client else ""
    if client not in ("127.0.0.1", "::1", "localhost"):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    task_id = request.path_params["task_id"]
    body = await request.json()
    granted = context.store().grant(task_id, body.get("capabilities", []))
    return JSONResponse({"ok": True, "task_id": task_id, "capabilities": sorted(granted)})


@mcp.tool()
def search_customer(task_id: str, q: str) -> dict:
    """Find customers by name, email, or code fragment."""
    return customer_order_tools.search_customer(task_id, q)


@mcp.tool()
def get_customer(task_id: str, customer_id: str) -> dict:
    """One customer by UUID."""
    return customer_order_tools.get_customer(task_id, customer_id)


@mcp.tool()
def search_order(task_id: str, customer_id: str, q: str = "") -> dict:
    """Orders of one customer, optionally filtered by code fragment."""
    return customer_order_tools.search_order(task_id, customer_id, q)


@mcp.tool()
def get_order(task_id: str, order_id: str) -> dict:
    """One order with items."""
    return customer_order_tools.get_order(task_id, order_id)


@mcp.tool()
def get_ticket(task_id: str, ticket_id: str) -> dict:
    """One ticket by UUID."""
    return ticket_policy_tools.get_ticket(task_id, ticket_id)


@mcp.tool()
def get_policy(task_id: str, rule_key: str) -> dict:
    """One policy rule by key."""
    return ticket_policy_tools.get_policy(task_id, rule_key)


@mcp.tool()
def api_get(task_id: str, path: str, params: dict | None = None) -> dict:
    """Fallback GET against an allowlisted read path."""
    return ticket_policy_tools.api_get(task_id, path, params or {})


@mcp.tool()
def inspect_state(task_id: str, kind: str, key: str, extra: dict | None = None) -> dict:
    """Probe committed state: mutation key or business identity."""
    return probe_tools.inspect_state(task_id, kind, key, extra or {})


@mcp.tool()
async def browser_open(task_id: str, target: str = "ops", headless: bool = True) -> dict:
    """Open (or reuse) the task's browser session."""
    return await session_tools.browser_open(task_id, target, headless)


@mcp.tool()
async def browser_navigate(task_id: str, route: str) -> dict:
    """Navigate inside the URL guard."""
    return await session_tools.browser_navigate(task_id, route)


@mcp.tool()
async def browser_observe(task_id: str) -> dict:
    """Fresh accessibility observation."""
    return await session_tools.browser_observe(task_id)


@mcp.tool()
async def browser_click(task_id: str, ref: str) -> dict:
    """Click a ref (page state only)."""
    return await act_tools.browser_click(task_id, ref)


@mcp.tool()
async def browser_fill(task_id: str, ref: str, value: str) -> dict:
    """Fill a ref (form state only)."""
    return await act_tools.browser_fill(task_id, ref, value)


@mcp.tool()
async def browser_submit(
    task_id: str, ref: str, mutation_key: str, token: str, params: dict
) -> dict:
    """Commit the effect form (token-gated; the only write path)."""
    return await act_tools.browser_submit(task_id, ref, mutation_key, token, params)


@mcp.tool()
async def browser_back(task_id: str) -> dict:
    """Browser back navigation."""
    return await session_tools.browser_back(task_id)


@mcp.tool()
async def browser_screenshot(task_id: str, label: str) -> dict:
    """Labeled screenshot into the run's evidence trail."""
    return await session_tools.browser_screenshot(task_id, label)


def main() -> None:
    """Serve SSE (plus the admin route) for agent clients."""
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
