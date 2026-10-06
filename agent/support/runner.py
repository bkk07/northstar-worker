"""Supervisor runner: ticket → classify → workflow → outcome (spec Phase 8).

`run_ticket` is the single entry point the Phase 9 API/HITL layer will
call. It takes an optional LLM client (Groq live, `None` for the
deterministic mock path) and an optional `tools` map (live Phase 7 tools
by default, fakes in tests). Progress is posted back to the ticket as one
AI_AGENT message so the console timeline shows agent activity; posting is
best-effort and never fails a run.
"""

from agent.support import workflows
from agent.support.classifier import classify
from agent.support.state import SupportState, fresh_state
from mcp_server.support import ticket_tools

_ACTION_WORKFLOWS = {
    "REFUND": workflows.refund_workflow,
    "REPLACEMENT": workflows.replacement_workflow,
    "RETURN": workflows.return_workflow,
    "CANCELLATION": workflows.cancellation_workflow,
}


def _note_best_effort(ticket_id: str, message: str) -> None:
    try:
        ticket_tools.add_ticket_message(ticket_id, message, "AI_AGENT")
    except Exception:
        pass


def run_ticket(ticket_id: str, *, llm=None, tools: dict | None = None) -> SupportState:
    """Run the supervisor + one specialized workflow for a ticket."""
    tools = tools or workflows.default_tools()
    state = fresh_state(ticket_id)

    loaded = tools.get("get_ticket")
    if loaded is None:
        state["decision"] = "needs_human"
        state["resolution"] = "Ticket context is unavailable."
        return state
    envelope = loaded(ticket_id)
    state["tool_results"].append({"tool": "get_ticket", "ok": envelope.get("ok")})
    if not envelope.get("ok"):
        state["decision"] = "needs_human"
        state["resolution"] = "I could not load this ticket — a support agent will take over."
        return state

    ticket = envelope["ticket"]
    state["user_id"] = ticket["customer"]["id"]
    related = ticket.get("related_order") or {}
    state["order_id"] = related.get("id")
    state["customer_context"] = {"name": ticket["customer"]["name"]}
    if related:
        state["order_context"] = {"order_number": related.get("order_number")}

    verdict = classify(ticket["subject"], ticket["description"], ticket["category"], llm)
    state["intent"] = verdict.intent
    order_id = verdict.order_id or state["order_id"]

    if verdict.intent in _ACTION_WORKFLOWS:
        if not order_id:
            state["decision"] = "ask_customer"
            state["resolution"] = (
                "Could you share the order number this is about? "
                "I can then check the policy and act right away."
            )
        else:
            _ACTION_WORKFLOWS[verdict.intent](
                state, order_id, verdict.confidence, tools, llm
            )
    elif verdict.intent in ("ORDER_STATUS", "DELIVERY", "PAYMENT"):
        workflows.tracking_workflow(state, order_id, tools, llm)
    else:
        workflows.general_workflow(state, ticket["subject"], tools, llm)

    if state.get("resolution"):
        _note_best_effort(ticket_id, state["resolution"])
    return state
