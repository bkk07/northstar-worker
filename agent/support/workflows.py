"""Specialized workflows: REFUND / REPLACEMENT / RETURN / CANCELLATION /
ORDER-DELIVERY / GENERAL (spec Phase 8).

Each workflow loads context through the injected `tools` map (Phase 7
envelopes), checks policy eligibility, proposes an action, pauses for
approval when the policy says so, executes low-risk actions, and verifies
by re-checking eligibility. Tool failures route to a human, never to a
guess. Reply text uses the LLM when provided, else deterministic templates.
"""

from agent.support import approval as approval_policy
from mcp_server.support import (
    action_tools,
    knowledge_tools,
    order_tools,
    policy_tools,
    ticket_tools,
)

_Response = str


def default_tools() -> dict:
    """Live tool map: local calls into the Phase 7 business tools."""
    return {
        "get_ticket": ticket_tools.get_ticket,
        "check_refund_eligibility": policy_tools.check_refund_eligibility,
        "check_return_eligibility": policy_tools.check_return_eligibility,
        "check_replacement_eligibility": policy_tools.check_replacement_eligibility,
        "check_cancellation_eligibility": policy_tools.check_cancellation_eligibility,
        "mock_refund": action_tools.mock_refund,
        "mock_return": action_tools.mock_return,
        "mock_replace": action_tools.mock_replace,
        "mock_cancel_order": action_tools.mock_cancel_order,
        "get_order": order_tools.get_order,
        "get_order_tracking": order_tools.get_order_tracking,
        "search_knowledge": knowledge_tools.search_knowledge,
    }


def _trace(state: dict, tool: str, envelope: dict) -> dict:
    """Record a tool call; return the envelope."""
    state.setdefault("tool_results", []).append({"tool": tool, "ok": envelope.get("ok")})
    return envelope


def _fail_human(state: dict, reason: str) -> dict:
    """Route to a human when a tool fails (never guess)."""
    state["decision"] = "needs_human"
    state["approval_required"] = True
    state["approval_status"] = None
    state["resolution"] = (
        f"I need a human to take over: {reason}. "
        "A support agent will follow up shortly."
    )
    return state


def _draft(llm, template: str, context: str) -> _Response:
    """LLM reply draft with template fallback (LLM failures never break runs)."""
    if llm is None:
        return template
    try:
        return llm.complete(
            "You write short, warm ecommerce support replies (2-4 sentences).",
            context,
        )
    except Exception:
        return template


def _mutation_key(state: dict, action: str) -> str:
    """Deterministic key: retries collide instead of duplicating."""
    return f"agent:{state['ticket_id']}:{action.lower()}"


def _run_action_workflow(
    *,
    state: dict,
    tools: dict,
    llm,
    confidence: float,
    action_type: str,
    check_tool: str,
    mock_tool: str,
    order_id: str,
    success_template: str,
) -> dict:
    check = _trace(state, check_tool, tools[check_tool](order_id))
    if not check.get("ok"):
        return _fail_human(state, f"{check_tool} failed")
    state["policy_context"] = {
        "action": action_type,
        "eligible": check.get("eligible"),
        "reasons": check.get("reasons", []),
    }
    if not check.get("eligible"):
        reasons = "; ".join(check.get("reasons", []))
        state["decision"] = "ineligible"
        state["resolution"] = _draft(
            llm,
            f"I checked the policy for order {check.get('order_number')}: {reasons}. "
            "A support agent can review alternatives.",
            f"Explain ineligibility: {reasons}",
        )
        return state

    amount = 0
    if action_type == "REFUND":
        detail = _trace(state, "get_order", tools["get_order"](order_id))
        if not detail.get("ok"):
            return _fail_human(state, "get_order failed")
        amount = detail["order"]["total_paise"]
        state["order_context"] = {"total_paise": amount}

    required, reason = approval_policy.needs_approval(
        action_type=action_type, amount_paise=amount, confidence=confidence
    )
    state["proposed_action"] = {
        "action_type": action_type,
        "order_id": order_id,
        "reason": reason or "eligible under policy",
        "amount_paise": amount or None,
    }
    if required:
        state["decision"] = "awaiting_approval"
        state["approval_required"] = True
        state["resolution"] = _draft(
            llm,
            f"This needs a quick human approval ({reason}). "
            "I'll proceed as soon as support confirms.",
            f"Explain approval pause: {reason}",
        )
        return state

    ticket_id = state["ticket_id"]
    if action_type == "REFUND":
        executed = tools[mock_tool](
            order_id, _mutation_key(state, action_type), ticket_id, amount
        )
    else:
        executed = tools[mock_tool](order_id, _mutation_key(state, action_type), ticket_id)
    executed = _trace(state, mock_tool, executed)
    if not executed.get("ok"):
        return _fail_human(state, f"{mock_tool} failed: {executed.get('error')}")
    state["action_result"] = executed.get("action")

    verify = _trace(state, check_tool, tools[check_tool](order_id))
    if verify.get("ok") and verify.get("eligible"):
        return _fail_human(state, "verification failed after execution")
    state["decision"] = "resolved_ready"
    state["resolution"] = _draft(llm, success_template, f"Confirm success: {success_template}")
    return state


def refund_workflow(state: dict, order_id: str, confidence: float, tools: dict, llm=None) -> dict:
    """Ticket → refund eligibility → approve-or-pause → mock refund → verify."""
    return _run_action_workflow(
        state=state,
        tools=tools,
        llm=llm,
        confidence=confidence,
        action_type="REFUND",
        check_tool="check_refund_eligibility",
        mock_tool="mock_refund",
        order_id=order_id,
        success_template="Your refund is done — it goes back to the original payment method.",
    )


def replacement_workflow(
    state: dict, order_id: str, confidence: float, tools: dict, llm=None
) -> dict:
    """Ticket → replacement eligibility → approve-or-pause → mock replace → verify."""
    return _run_action_workflow(
        state=state,
        tools=tools,
        llm=llm,
        confidence=confidence,
        action_type="REPLACE",
        check_tool="check_replacement_eligibility",
        mock_tool="mock_replace",
        order_id=order_id,
        success_template="Your replacement is arranged — it ships to your address.",
    )


def return_workflow(state: dict, order_id: str, confidence: float, tools: dict, llm=None) -> dict:
    """Ticket → return eligibility → approve-or-pause → mock return → verify."""
    return _run_action_workflow(
        state=state,
        tools=tools,
        llm=llm,
        confidence=confidence,
        action_type="RETURN",
        check_tool="check_return_eligibility",
        mock_tool="mock_return",
        order_id=order_id,
        success_template="Your return is registered — keep the item packed for pickup.",
    )


def cancellation_workflow(
    state: dict, order_id: str, confidence: float, tools: dict, llm=None
) -> dict:
    """Ticket → cancellation eligibility → mock cancel → verify."""
    return _run_action_workflow(
        state=state,
        tools=tools,
        llm=llm,
        confidence=confidence,
        action_type="CANCEL",
        check_tool="check_cancellation_eligibility",
        mock_tool="mock_cancel_order",
        order_id=order_id,
        success_template="Your order is cancelled — no money was captured.",
    )


def tracking_workflow(state: dict, order_id: str | None, tools: dict, llm=None) -> dict:
    """Order/delivery/payment status answer (read-only, never acts)."""
    if not order_id:
        state["decision"] = "ask_customer"
        state["resolution"] = "Could you share your order number so I can track it?"
        return state
    tracking = _trace(state, "get_order_tracking", tools["get_order_tracking"](order_id))
    if not tracking.get("ok"):
        return _fail_human(state, "get_order_tracking failed")
    state["order_context"] = {"status": tracking.get("status")}
    steps = [s["label"] for s in tracking.get("timeline", []) if s.get("done")]
    template = (
        f"Order {tracking.get('order_number')} is {tracking.get('status')}. "
        f"Done so far: {', '.join(steps)}. "
        f"Estimated delivery: {tracking.get('estimated_delivery')}."
    )
    state["decision"] = "answered"
    state["resolution"] = _draft(llm, template, f"Relay tracking update: {template}")
    return state


def general_workflow(state: dict, subject: str, tools: dict, llm=None) -> dict:
    """Knowledge-backed answer (read-only, never acts)."""
    search = _trace(state, "search_knowledge", tools["search_knowledge"](subject))
    hits = search.get("results", []) if search.get("ok") else []
    if hits:
        top = hits[0]
        template = f"Here's what I found ({top['source']}): {top['snippet']}"
    else:
        template = "Thanks for reaching out — a support agent will pick this up shortly."
    state["decision"] = "answered"
    state["resolution"] = _draft(llm, template, f"Answer generally: {template}")
    return state
