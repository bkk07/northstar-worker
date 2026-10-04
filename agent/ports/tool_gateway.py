"""ToolGateway port: the agent-side contract for world interaction.

One typed method per §14 tool. Implementations (the MCP adapter in
Phase 11, fakes in agent tests later) honor these signatures; graph nodes
depend on this Protocol, never on a concrete gateway.
"""

from typing import Protocol


class ToolGateway(Protocol):
    """Typed boundary between reasoning (agent) and acting (tools)."""

    def search_customer(self, task_id: str, q: str) -> dict:
        """Find customers (empty and multi-match are data)."""
        ...

    def get_customer(self, task_id: str, customer_id: str) -> dict:
        """One customer by UUID."""
        ...

    def search_order(self, task_id: str, customer_id: str, q: str = "") -> dict:
        """Orders of one customer, optionally filtered."""
        ...

    def get_order(self, task_id: str, order_id: str) -> dict:
        """One order with items."""
        ...

    def get_ticket(self, task_id: str, ticket_id: str) -> dict:
        """One ticket by UUID."""
        ...

    def get_policy(self, task_id: str, rule_key: str) -> dict:
        """One policy rule by key."""
        ...

    def api_get(self, task_id: str, path: str, params: dict | None = None) -> dict:
        """Fallback GET against an allowlisted read path."""
        ...

    def inspect_state(self, task_id: str, kind: str, key: str, extra: dict | None = None) -> dict:
        """Probe committed state (mutation key or business identity)."""
        ...

    def browser_open(self, task_id: str, target: str = "ops", headless: bool = True) -> dict:
        """Open (or reuse) the task's browser session."""
        ...

    def browser_navigate(self, task_id: str, route: str) -> dict:
        """Navigate inside the URL guard."""
        ...

    def browser_observe(self, task_id: str) -> dict:
        """Fresh accessibility observation."""
        ...

    def browser_click(self, task_id: str, ref: str) -> dict:
        """Click a ref (page state only)."""
        ...

    def browser_fill(self, task_id: str, ref: str, value: str) -> dict:
        """Fill a ref (form state only)."""
        ...

    def browser_submit(
        self, task_id: str, ref: str, mutation_key: str, token: str, params: dict
    ) -> dict:
        """Commit the effect form (token-gated)."""
        ...

    def browser_back(self, task_id: str) -> dict:
        """Browser back navigation."""
        ...

    def browser_screenshot(self, task_id: str, label: str) -> dict:
        """Labeled screenshot into the run's evidence trail."""
        ...
