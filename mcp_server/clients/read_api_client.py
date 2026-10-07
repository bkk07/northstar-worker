"""GET-only read client for the commerce API (no DB credentials here).

All MCP reads go through `GET /api/read/*` (or `/api/shop/*` fallback).
Anything else — control plane, ops writes, worker API — is rejected.
"""

import httpx

ALLOWED_PREFIXES = ("/api/read/", "/api/shop/")


class ReadApiClient:
    """Thin typed wrapper over the backend read API."""

    def __init__(
        self, base_url: str, timeout_seconds: float = 10.0, api_token: str | None = None
    ) -> None:
        headers = {"Authorization": f"Bearer {api_token}"} if api_token else {}
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout_seconds, headers=headers
        )

    def _get(self, path: str, params: dict | None = None):
        response = self._client.get(path, params=params or {})
        if response.status_code == 404:
            raise LookupError(f"not_found: {path}")
        response.raise_for_status()
        return response.json()

    def search_customers(self, q: str) -> list:
        """Customer search (look-alikes included)."""
        return self._get("/api/read/customers", {"q": q})

    def get_customer(self, customer_id: str):
        """One customer by UUID."""
        return self._get(f"/api/read/customers/{customer_id}")

    def search_orders(self, customer_id: str, q: str = "") -> list:
        """Orders of one customer, optionally filtered by code fragment."""
        orders = self._get("/api/read/orders", {"customer_id": customer_id})
        if q:
            needle = q.lower()
            orders = [o for o in orders if needle in o.get("code", "").lower()]
        return orders

    def get_order(self, order_id: str):
        """One order with items."""
        return self._get(f"/api/read/orders/{order_id}")

    def get_ticket(self, ticket_id: str):
        """One ticket."""
        return self._get(f"/api/read/tickets/{ticket_id}")

    def get_policy(self, rule_key: str):
        """One policy rule by key (unknown keys list what exists)."""
        policies = self._get("/api/read/policies")
        for policy in policies:
            if policy.get("rule_key") == rule_key:
                return policy
        known = sorted(str(p.get("rule_key", "")) for p in policies)
        raise LookupError(f"not_found: policy {rule_key} (known: {', '.join(known)})")

    def probe_mutation(self, key: str) -> dict:
        """Probe an idempotency key."""
        return self._get(f"/api/read/probe/mutation/{key}")

    def probe_replacement(self, order_item_id: str) -> dict:
        """Probe the active replacement for an order item."""
        return self._get("/api/read/probe/replacement", {"order_item_id": order_item_id})

    def probe_refund(self, ticket_id: str, order_id: str) -> dict:
        """Probe the active refund for a (ticket, order) identity."""
        return self._get("/api/read/probe/refund", {"ticket_id": ticket_id, "order_id": order_id})

    def api_get(self, path: str, params: dict | None = None):
        """Fallback GET restricted to the read allowlist."""
        if not path.startswith(ALLOWED_PREFIXES):
            raise PermissionError(
                f"rejected: path outside read allowlist: {path} "
                f"(allowed prefixes: {', '.join(ALLOWED_PREFIXES)})"
            )
        return self._get(path, params)
