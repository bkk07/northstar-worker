"""Oracle client: independent truth over HTTP (Phase 27).

Wraps the control-plane oracle plus the public code-resolution and
business reads the harness needs for actual-effects measurement. HTTP
only (httpx) — this module never imports the agent, the backend app,
or the database; the isolation test pins that.
"""

from __future__ import annotations

import httpx


class OracleClient:
    """Control oracle + public reads, all over HTTP."""

    def __init__(
        self,
        backend_url: str,
        operator_token: str,
        timeout_s: float = 15.0,
    ) -> None:
        self._backend = backend_url.rstrip("/")
        self._operator = {"Authorization": f"Bearer {operator_token}"}
        self._timeout = timeout_s
        self._client = httpx.Client(timeout=timeout_s)
        login = self._client.post(
            f"{self._backend}/api/ops/auth/login", json={"agent_name": "eval-harness"}
        )
        login.raise_for_status()

    def close(self) -> None:
        """Release the session (cookie jar included)."""
        self._client.close()

    def expected(self, scenario_id: str) -> dict:
        """Oracle (outcome, effects) for one scenario id."""
        response = self._client.get(
            f"{self._backend}/api/control/oracle/{scenario_id}",
            headers=self._operator,
        )
        response.raise_for_status()
        return response.json()

    def order_by_code(self, order_code: str) -> dict:
        """Order (with items) for an order code (public ops read)."""
        response = self._client.get(f"{self._backend}/api/ops/orders/{order_code}")
        response.raise_for_status()
        return response.json()

    def ticket_by_code(self, ticket_code: str) -> dict:
        """Ticket row for a ticket code (public ops read)."""
        response = self._client.get(f"{self._backend}/api/ops/tickets/{ticket_code}")
        response.raise_for_status()
        return response.json()

    def refunds_for_order(self, order_id: str) -> list[dict]:
        """Active refunds for one order (public commerce read)."""
        response = self._client.get(
            f"{self._backend}/api/read/refunds", params={"order_id": order_id}
        )
        response.raise_for_status()
        return response.json()

    def refunds_for_ticket(self, ticket_id: str) -> list[dict]:
        """Refunds for one ticket (public commerce read)."""
        response = self._client.get(
            f"{self._backend}/api/read/refunds", params={"ticket_id": ticket_id}
        )
        response.raise_for_status()
        return response.json()

    def replacements_for_item(self, order_item_id: str) -> list[dict]:
        """Replacements for one order item (public commerce read)."""
        response = self._client.get(
            f"{self._backend}/api/read/replacements",
            params={"order_item_id": order_item_id},
        )
        response.raise_for_status()
        return response.json()
