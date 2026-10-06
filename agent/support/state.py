"""Agent state (spec Phase 8): structured workflow state, LangGraph-ready."""

from typing import Any, TypedDict


class SupportState(TypedDict, total=False):
    """State carried through supervisor → workflow → verify."""

    ticket_id: str
    user_id: str
    order_id: str | None
    intent: str
    messages: list[dict[str, str]]
    customer_context: dict[str, Any]
    order_context: dict[str, Any]
    product_context: dict[str, Any]
    policy_context: dict[str, Any]
    tool_results: list[dict[str, Any]]
    decision: str | None
    proposed_action: dict[str, Any] | None
    approval_required: bool
    approval_status: str | None
    action_result: dict[str, Any] | None
    resolution: str | None
    escalated: bool


def fresh_state(ticket_id: str) -> SupportState:
    """Initial state for one ticket run."""
    return SupportState(
        ticket_id=ticket_id,
        user_id="",
        order_id=None,
        intent="",
        messages=[],
        customer_context={},
        order_context={},
        product_context={},
        policy_context={},
        tool_results=[],
        decision=None,
        proposed_action=None,
        approval_required=False,
        approval_status=None,
        action_result=None,
        resolution=None,
        escalated=False,
    )
