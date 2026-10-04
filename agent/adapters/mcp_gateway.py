"""MCP adapter: ToolGateway over SSE (one connection per call).

Per-call connections keep the adapter stateless (no loop/thread juggling);
local SSE handshake cost is milliseconds. A persistent session is a later
optimization, not a correctness need.
"""

import asyncio
import json

from mcp import ClientSession
from mcp.client.sse import sse_client


class MCPToolGateway:
    """Agent-side gateway speaking MCP to the tool server process."""

    def __init__(self, server_url: str = "http://127.0.0.1:8002", timeout: float = 30.0) -> None:
        self._url = server_url.rstrip("/")
        self._timeout = timeout

    def _call(self, tool: str, args: dict) -> dict:
        try:
            return asyncio.run(self._acall(tool, args))
        except BaseExceptionGroup as exc:
            raise RuntimeError(self._leaf_message(exc)) from None

    @staticmethod
    def _leaf_message(exc: BaseExceptionGroup) -> str:
        """Unwrap anyio task-group noise to the tool error text."""
        leaf: BaseException = exc
        while isinstance(leaf, BaseExceptionGroup) and leaf.exceptions:
            leaf = leaf.exceptions[0]
        return str(leaf) or type(leaf).__name__

    async def _acall(self, tool: str, args: dict) -> dict:
        async with sse_client(f"{self._url}/sse", timeout=self._timeout) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, args)
                return _payload(tool, result)

    def search_customer(self, task_id: str, q: str) -> dict:
        """Find customers (empty and multi-match are data)."""
        return self._call("search_customer", {"task_id": task_id, "q": q})

    def get_customer(self, task_id: str, customer_id: str) -> dict:
        """One customer by UUID."""
        return self._call("get_customer", {"task_id": task_id, "customer_id": customer_id})

    def search_order(self, task_id: str, customer_id: str, q: str = "") -> dict:
        """Orders of one customer, optionally filtered."""
        return self._call("search_order", {"task_id": task_id, "customer_id": customer_id, "q": q})

    def get_order(self, task_id: str, order_id: str) -> dict:
        """One order with items."""
        return self._call("get_order", {"task_id": task_id, "order_id": order_id})

    def get_ticket(self, task_id: str, ticket_id: str) -> dict:
        """One ticket by UUID."""
        return self._call("get_ticket", {"task_id": task_id, "ticket_id": ticket_id})

    def get_policy(self, task_id: str, rule_key: str) -> dict:
        """One policy rule by key."""
        return self._call("get_policy", {"task_id": task_id, "rule_key": rule_key})

    def api_get(self, task_id: str, path: str, params: dict | None = None) -> dict:
        """Fallback GET against an allowlisted read path."""
        return self._call("api_get", {"task_id": task_id, "path": path, "params": params or {}})

    def inspect_state(self, task_id: str, kind: str, key: str, extra: dict | None = None) -> dict:
        """Probe committed state (mutation key or business identity)."""
        return self._call(
            "inspect_state",
            {"task_id": task_id, "kind": kind, "key": key, "extra": extra or {}},
        )

    def browser_open(self, task_id: str, target: str = "ops", headless: bool = True) -> dict:
        """Open (or reuse) the task's browser session."""
        return self._call(
            "browser_open", {"task_id": task_id, "target": target, "headless": headless}
        )

    def browser_navigate(self, task_id: str, route: str) -> dict:
        """Navigate inside the URL guard."""
        return self._call("browser_navigate", {"task_id": task_id, "route": route})

    def browser_observe(self, task_id: str) -> dict:
        """Fresh accessibility observation."""
        return self._call("browser_observe", {"task_id": task_id})

    def browser_click(self, task_id: str, ref: str) -> dict:
        """Click a ref (page state only)."""
        return self._call("browser_click", {"task_id": task_id, "ref": ref})

    def browser_fill(self, task_id: str, ref: str, value: str) -> dict:
        """Fill a ref (form state only)."""
        return self._call("browser_fill", {"task_id": task_id, "ref": ref, "value": value})

    def browser_submit(
        self, task_id: str, ref: str, mutation_key: str, token: str, params: dict
    ) -> dict:
        """Commit the effect form (token-gated)."""
        return self._call(
            "browser_submit",
            {
                "task_id": task_id,
                "ref": ref,
                "mutation_key": mutation_key,
                "token": token,
                "params": params,
            },
        )

    def browser_back(self, task_id: str) -> dict:
        """Browser back navigation."""
        return self._call("browser_back", {"task_id": task_id})

    def browser_screenshot(self, task_id: str, label: str) -> dict:
        """Labeled screenshot into the run's evidence trail."""
        return self._call("browser_screenshot", {"task_id": task_id, "label": label})

    def list_tool_names(self) -> list[str]:
        """Tool names on the server (introspection/admin use, not agent path)."""
        return asyncio.run(self._alist())

    async def _alist(self) -> list[str]:
        async with sse_client(f"{self._url}/sse", timeout=self._timeout) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                return [tool.name for tool in tools.tools]


def _payload(tool: str, result) -> dict:
    """Unpack a CallToolResult: error payloads raise, data returns."""
    structured = getattr(result, "structuredContent", None)
    if getattr(result, "isError", False):
        raise RuntimeError(_text_of(result, structured) or f"tool {tool} failed")
    if isinstance(structured, dict) and structured:
        return structured
    text = _text_of(result, structured)
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {"result": parsed}
    except (TypeError, ValueError):
        return {"text": text or ""}


def _text_of(result, structured) -> str:
    blocks = getattr(result, "content", []) or []
    texts = [getattr(block, "text", "") for block in blocks if hasattr(block, "text")]
    combined = "\n".join(t for t in texts if t)
    if combined:
        return combined
    if isinstance(structured, dict):
        return json.dumps(structured)
    return ""
