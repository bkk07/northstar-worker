"""Support tool registry: the closed business-tool catalogue (spec Phase 7).

Mirrors `mcp_server/registry.py` for the task plane: name → capability →
side effects → idempotency. A unit test asserts the live support server
exposes exactly these tools.
"""

from dataclasses import dataclass

SUPPORT_CAPABILITIES = frozenset({"support.read", "support.act"})


@dataclass(frozen=True)
class SupportToolSpec:
    """One business tool's contract."""

    name: str
    group: str
    read_only: bool
    side_effect: str
    idempotency: str


SUPPORT_TOOL_SPECS: tuple[SupportToolSpec, ...] = (
    # USER
    SupportToolSpec("get_user", "USER", True, "none", "n/a"),
    SupportToolSpec("get_user_orders", "USER", True, "none", "n/a"),
    SupportToolSpec("get_user_tickets", "USER", True, "none", "n/a"),
    # ORDER
    SupportToolSpec("get_order", "ORDER", True, "none", "n/a"),
    SupportToolSpec("get_order_items", "ORDER", True, "none", "n/a"),
    SupportToolSpec("get_order_status", "ORDER", True, "none", "n/a"),
    SupportToolSpec("get_order_tracking", "ORDER", True, "none", "n/a"),
    # PRODUCT
    SupportToolSpec("get_product", "PRODUCT", True, "none", "n/a"),
    SupportToolSpec("get_product_details", "PRODUCT", True, "none", "n/a"),
    SupportToolSpec("get_product_policy", "PRODUCT", True, "none", "n/a"),
    # POLICY
    SupportToolSpec("check_refund_eligibility", "POLICY", True, "none", "n/a"),
    SupportToolSpec("check_return_eligibility", "POLICY", True, "none", "n/a"),
    SupportToolSpec(
        "check_replacement_eligibility", "POLICY", True, "none", "n/a"
    ),
    SupportToolSpec(
        "check_cancellation_eligibility", "POLICY", True, "none", "n/a"
    ),
    # ACTIONS
    SupportToolSpec(
        "mock_refund", "ACTIONS", False, "refund row", "mutation_key + DB unique"
    ),
    SupportToolSpec(
        "mock_return", "ACTIONS", False, "return row + RETURNED", "mutation_key + DB unique"
    ),
    SupportToolSpec(
        "mock_replace", "ACTIONS", False, "replacement row", "mutation_key + DB unique"
    ),
    SupportToolSpec(
        "mock_cancel_order",
        "ACTIONS",
        False,
        "cancel row + CANCELLED",
        "mutation_key + DB unique",
    ),
    # TICKET
    SupportToolSpec("get_ticket", "TICKET", True, "none", "n/a"),
    SupportToolSpec("add_ticket_message", "TICKET", False, "message row", "n/a"),
    SupportToolSpec("update_ticket", "TICKET", False, "field update", "n/a"),
    SupportToolSpec("resolve_ticket", "TICKET", False, "RESOLVED", "terminal guard"),
    SupportToolSpec("escalate_ticket", "TICKET", False, "ESCALATED", "terminal guard"),
    # KNOWLEDGE
    SupportToolSpec("search_knowledge", "KNOWLEDGE", True, "none", "n/a"),
)

SUPPORT_TOOL_NAMES = frozenset(spec.name for spec in SUPPORT_TOOL_SPECS)


def spec_for(name: str) -> SupportToolSpec:
    """Spec for a tool name (KeyError when unknown — fail closed)."""
    for spec in SUPPORT_TOOL_SPECS:
        if spec.name == name:
            return spec
    raise KeyError(f"unknown support tool: {name}")
