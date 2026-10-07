"""Typed support-graph state: survives pause/HITL/restart/resume."""

from typing import Any, TypedDict


class SupportGraphState(TypedDict, total=False):
    """Full state for one ticket run. All values must stay JSON-serializable."""

    ticket_id: str
    user_id: str
    order_id: str | None
    intent: str
    confidence: float
    workflow: str
    ticket_subject: str
    ticket_description: str
    ticket_category: str
    tracking_context: dict[str, Any]
    messages: list[dict[str, str]]
    customer_context: dict[str, Any]
    order_context: dict[str, Any]
    product_context: dict[str, Any]
    policy_context: dict[str, Any]
    tool_results: list[dict[str, Any]]
    decision: str | None
    proposed_action: dict[str, Any] | None
    approval_required: bool
    approval_status: str | None  # None | pending | approved | rejected | expired
    human_feedback: str | None
    action_result: dict[str, Any] | None
    verification_result: dict[str, Any] | None
    resolution: str | None
    escalated: bool
    error: str | None
    retry_count: int


def fresh_graph_state(ticket_id: str) -> SupportGraphState:
    """Initial state for one ticket run."""
    return SupportGraphState(
        ticket_id=ticket_id,
        user_id="",
        order_id=None,
        intent="",
        confidence=0.0,
        workflow="",
        ticket_subject="",
        ticket_description="",
        ticket_category="GENERAL",
        tracking_context={},
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
        human_feedback=None,
        action_result=None,
        verification_result=None,
        resolution=None,
        escalated=False,
        error=None,
        retry_count=0,
    )
