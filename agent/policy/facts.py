"""Policy facts: everything the engine may read, from DB facts only.

Facts come from read tools (orders, tickets, customers, probes, policy
rows) — never from LLM free text. The engine receives one `Facts`
object; a `missing` list names anything the gatherer could not load, and
the engine fail-closes on it. Tests construct `Facts` by hand, so every
rule is provable without a database.
"""

from dataclasses import dataclass, field

from agent.policy import rules


@dataclass
class Facts:
    """Deterministic inputs for one authorization check."""

    customer_id: str = ""
    order: dict = field(default_factory=dict)
    ticket: dict = field(default_factory=dict)
    customer: dict = field(default_factory=dict)
    existing_replacement: dict | None = None
    existing_refund: dict | None = None
    order_refunds: list[dict] = field(default_factory=list)
    refunds_last_90d: int = 0
    policies: dict = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)

    def threshold(self, rule_key: str, param: str, default):
        """Seeded policy param, falling back to code defaults."""
        params = self.policies.get(rule_key, {})
        if param in params:
            return params[param]
        return rules.DEFAULTS.get(rule_key, {}).get(param, default)


def gather_facts(task_id: str, contract, action: dict, gateway) -> Facts:
    """Load facts for one action through read tools (no writes, no LLM)."""
    facts = Facts()
    _load_entities(task_id, contract, gateway, facts)
    _load_probes(task_id, action, gateway, facts)
    _load_order_refunds(task_id, contract, gateway, facts)
    _load_policies(task_id, gateway, facts)
    _load_refund_history(task_id, gateway, facts)
    return facts


def _safe(call, label: str, facts: Facts):
    try:
        return call()
    except Exception:
        facts.missing.append(label)
        return None


def _load_entities(task_id, contract, gateway, facts: Facts) -> None:
    if contract.customer_id:
        facts.customer_id = contract.customer_id
        customer = _safe(
            lambda: gateway.get_customer(task_id, contract.customer_id),
            "customer",
            facts,
        )
        if customer:
            facts.customer = _trusted_customer(customer.get("customer", {}))
    if contract.order_id:
        order = _safe(lambda: gateway.get_order(task_id, contract.order_id), "order", facts)
        if order:
            facts.order = _trusted_order(order.get("order", {}))
    if contract.ticket_id:
        ticket = _safe(lambda: gateway.get_ticket(task_id, contract.ticket_id), "ticket", facts)
        if ticket:
            facts.ticket = _trusted_ticket(ticket.get("ticket", {}))


# Ownership and eligibility read IDs, linkage, statuses, and amounts —
# never free text. The allowlists below drop customer-controlled fields
# (bodies, subjects) at the facts boundary, so untrusted prose cannot
# reach the engine even when a read tool returns it.
ORDER_FIELDS = frozenset(
    {
        "id",
        "code",
        "customer_id",
        "status",
        "total_paise",
        "paid_paise",
        "placed_at",
        "delivered_at",
        "items",
    }
)

ORDER_ITEM_FIELDS = frozenset({"id", "sku", "title", "qty", "unit_paise", "category"})

TICKET_FIELDS = frozenset(
    {"id", "code", "customer_id", "order_id", "category", "status", "version"}
)

CUSTOMER_FIELDS = frozenset({"id", "code", "name", "email"})


def _trusted_order(order: dict) -> dict:
    """Order facts minus free text (IDs, linkage, money, line structure)."""
    kept = {key: order.get(key) for key in ORDER_FIELDS if key in order}
    items = kept.get("items")
    if isinstance(items, list):
        kept["items"] = [
            {key: item.get(key) for key in ORDER_ITEM_FIELDS if key in item}
            for item in items
            if isinstance(item, dict)
        ]
    return kept


def _trusted_ticket(ticket: dict) -> dict:
    """Ticket facts minus free text (bodies and subjects never enter)."""
    return {key: ticket.get(key) for key in TICKET_FIELDS if key in ticket}


def _trusted_customer(customer: dict) -> dict:
    """Customer facts minus anything but identity and contact."""
    return {key: customer.get(key) for key in CUSTOMER_FIELDS if key in customer}


def _load_probes(task_id, action: dict, gateway, facts: Facts) -> None:
    params = action.get("params", {}) if isinstance(action, dict) else {}
    order_item_id = params.get("order_item_id", "")
    if order_item_id:
        probe = _safe(
            lambda: gateway.inspect_state(task_id, "replacement", order_item_id),
            "probe:replacement",
            facts,
        )
        if probe and probe.get("found"):
            facts.existing_replacement = probe
    ticket_id = params.get("ticket_id", "")
    order_id = params.get("order_id", "")
    if ticket_id and order_id:
        probe = _safe(
            lambda: gateway.inspect_state(task_id, "refund", ticket_id, {"order_id": order_id}),
            "probe:refund",
            facts,
        )
        if probe and probe.get("found"):
            facts.existing_refund = probe


def _load_order_refunds(task_id, contract, gateway, facts: Facts) -> None:
    """Active refunds on the contract order (same-amount duplicate trap)."""
    if not contract.order_id:
        return
    rows = _safe(
        lambda: gateway.api_get(task_id, "/api/read/refunds", {"order_id": contract.order_id}),
        "order_refunds",
        facts,
    )
    if rows is not None:
        facts.order_refunds = rows.get("result", [])


def _load_policies(task_id, gateway, facts: Facts) -> None:
    policies = _safe(lambda: gateway.api_get(task_id, "/api/read/policies"), "policies", facts)
    if policies:
        for row in policies.get("result", []):
            facts.policies[row.get("rule_key", "")] = row.get("params", {})


def _load_refund_history(task_id, gateway, facts: Facts) -> None:
    if not facts.customer_id:
        facts.missing.append("refund_history")
        return
    window = facts.threshold("P-REF-002", "window_days", rules.REF_WINDOW_DAYS)
    history = _safe(
        lambda: gateway.api_get(
            task_id,
            "/api/read/refunds",
            {"customer_id": facts.customer_id, "window_days": window},
        ),
        "refund_history",
        facts,
    )
    if history is None:
        return
    facts.refunds_last_90d = len(history.get("result", []))
