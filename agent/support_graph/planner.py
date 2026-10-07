"""Goal-oriented tool planning: only the tools each intent needs.

The supervisor picks a workflow; the workflow declares the minimal read set.
No ticket runs the full `get_user → get_orders → get_order → get_product →
get_policy` chain unless its intent actually requires it.
"""

# Minimal read tools per intent (mutation tools are added by the
# execute node only after policy + approval gating).
INTENT_TOOL_PLAN: dict[str, list[str]] = {
    "REFUND": ["get_order", "get_order_items", "get_product", "get_product_policy"],
    "REPLACEMENT": ["get_order", "get_order_items", "get_product", "get_product_policy"],
    "RETURN": ["get_order", "get_order_items", "get_product_policy"],
    "CANCELLATION": ["get_order", "get_order_status"],
    "ORDER_STATUS": ["get_order", "get_order_status"],
    "DELIVERY": ["get_order", "get_order_tracking"],
    "PAYMENT": ["get_order", "get_order_status"],
    "GENERAL_QUERY": [],
}

INTENT_WORKFLOW: dict[str, str] = {
    "REFUND": "REFUND",
    "REPLACEMENT": "REPLACE",
    "RETURN": "RETURN",
    "CANCELLATION": "CANCELLATION",
    "ORDER_STATUS": "TRACKING",
    "DELIVERY": "TRACKING",
    "PAYMENT": "TRACKING",
    "GENERAL_QUERY": "GENERAL",
}

# Policy check tool per action workflow.
WORKFLOW_CHECK_TOOL: dict[str, str] = {
    "REFUND": "check_refund_eligibility",
    "REPLACE": "check_replacement_eligibility",
    "RETURN": "check_return_eligibility",
    "CANCELLATION": "check_cancellation_eligibility",
}

# Mock mutation tool per action workflow.
WORKFLOW_MOCK_TOOL: dict[str, str] = {
    "REFUND": "mock_refund",
    "REPLACE": "mock_replace",
    "RETURN": "mock_return",
    "CANCELLATION": "mock_cancel_order",
}

ACTION_WORKFLOWS = frozenset({"REFUND", "REPLACE", "RETURN", "CANCELLATION"})


def plan_for_intent(intent: str) -> list[str]:
    """Minimal read-tool list for an intent (unknown → empty, fail closed)."""
    return list(INTENT_TOOL_PLAN.get(intent, []))


def workflow_for_intent(intent: str) -> str:
    """Workflow name for an intent (unknown → GENERAL)."""
    return INTENT_WORKFLOW.get(intent, "GENERAL")
