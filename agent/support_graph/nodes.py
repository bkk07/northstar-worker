"""Support-graph nodes: small, testable, reuse existing deterministic tools.

Each node takes `(state, tools, llm)` and returns a state delta dict.
The graph wires them; the runner injects live tools + tracing.
"""

from typing import Any

from agent.support import approval as approval_policy
from agent.support.classifier import classify
from agent.support_graph.planner import (
    ACTION_WORKFLOWS,
    WORKFLOW_CHECK_TOOL,
    WORKFLOW_MOCK_TOOL,
    plan_for_intent,
    workflow_for_intent,
)


def _trace(state: dict, tool: str, envelope: dict) -> dict:
    state.setdefault("tool_results", []).append({"tool": tool, "ok": envelope.get("ok")})
    return envelope


def _fail_human(state: dict, reason: str) -> dict:
    return {
        "decision": "needs_human",
        "approval_required": True,
        "escalated": True,
        "error": reason,
        "resolution": (
            f"I need a human to take over: {reason}. "
            "A support agent will follow up shortly."
        ),
    }


def _draft(llm, template: str, context: str) -> str:
    if llm is None:
        return template
    try:
        return llm.complete(
            "You write short, warm ecommerce support replies (2-4 sentences).",
            context,
        )
    except Exception:
        return template


def load_ticket(state: dict, tools: dict, llm=None) -> dict:
    """Load ticket + customer/order identity."""
    get_ticket = tools.get("get_ticket")
    if get_ticket is None:
        return _fail_human(state, "ticket context unavailable")
    envelope = _trace(state, "get_ticket", get_ticket(state["ticket_id"]))
    if not envelope.get("ok"):
        return _fail_human(state, "could not load ticket")
    ticket = envelope["ticket"]
    delta: dict[str, Any] = {
        "user_id": ticket["customer"]["id"],
        "customer_context": {"name": ticket["customer"]["name"]},
        "messages": [
            {"role": "customer", "content": f"{ticket['subject']}\n{ticket['description']}"}
        ],
    }
    related = ticket.get("related_order") or {}
    if related:
        delta["order_id"] = related.get("id")
        delta["order_context"] = {"order_number": related.get("order_number")}
    delta["_ticket"] = {
        "subject": ticket["subject"],
        "description": ticket["description"],
        "category": ticket.get("category", "GENERAL"),
    }
    delta["ticket_subject"] = ticket["subject"]
    delta["ticket_description"] = ticket["description"]
    delta["ticket_category"] = ticket.get("category", "GENERAL")
    return delta


def supervise(state: dict, tools: dict, llm=None) -> dict:
    """Supervisor: classify intent + pick workflow (REFUND/REPLACE/...)."""
    subject = state.get("ticket_subject") or (state.get("_ticket") or {}).get("subject", "")
    description = state.get("ticket_description") or (state.get("_ticket") or {}).get("description", "")
    category = state.get("ticket_category") or (state.get("_ticket") or {}).get("category", "")
    verdict = classify(subject, description, category, llm)
    workflow = workflow_for_intent(verdict.intent)
    delta: dict[str, Any] = {
        "intent": verdict.intent,
        "confidence": verdict.confidence,
        "workflow": workflow,
    }
    order_id = verdict.order_id or state.get("order_id")
    if order_id:
        delta["order_id"] = order_id
    if verdict.intent in ("REFUND", "REPLACEMENT", "RETURN", "CANCELLATION") and not order_id:
        delta["decision"] = "ask_customer"
        delta["resolution"] = (
            "Could you share the order number this is about? "
            "I can then check the policy and act right away."
        )
    return delta


def gather(state: dict, tools: dict, llm=None) -> dict:
    """Goal-oriented context load: only the tools this intent needs."""
    if state.get("decision") == "ask_customer":
        return {}
    intent = state.get("intent", "")
    order_id = state.get("order_id")
    if intent in ("ORDER_STATUS", "DELIVERY", "PAYMENT", "TRACKING"):
        if not order_id:
            return {
                "decision": "ask_customer",
                "resolution": "Could you share your order number so I can track it?",
            }
        tracking_tool = tools.get("get_order_tracking")
        if tracking_tool is None:
            return _fail_human(state, "tracking tool unavailable")
        tracking = _trace(state, "get_order_tracking", tracking_tool(order_id))
        if not tracking.get("ok"):
            return _fail_human(state, "get_order_tracking failed")
        return {"order_context": {"status": tracking.get("status"), **(state.get("order_context") or {})},
                "_tracking": tracking, "tracking_context": tracking}
    if intent == "GENERAL_QUERY" or state.get("workflow") == "GENERAL":
        search = tools.get("search_knowledge")
        subject = (state.get("_ticket") or {}).get("subject", "")
        if search is None:
            return {"decision": "answered",
                    "resolution": "Thanks for reaching out — a support agent will pick this up shortly."}
        result = _trace(state, "search_knowledge", search(subject))
        hits = result.get("results", []) if result.get("ok") else []
        if hits:
            top = hits[0]
            template = f"Here's what I found ({top['source']}): {top['snippet']}"
        else:
            template = "Thanks for reaching out — a support agent will pick this up shortly."
        return {"decision": "answered", "resolution": _draft(llm, template, f"Answer generally: {template}")}
    # Action intents: load only planned reads.
    needed = plan_for_intent(intent)
    delta: dict[str, Any] = {}
    for tool_name in needed:
        fn = tools.get(tool_name)
        if fn is None:
            continue  # optional enrichment missing → policy check still gates
        arg: Any = order_id
        if tool_name in ("get_product", "get_product_details"):
            # Product id unknown until order items load; skip here, policy
            # tools resolve product internally from order.
            continue
        if tool_name == "get_product_policy":
            continue  # covered by check_*_eligibility below
        try:
            envelope = _trace(state, tool_name, fn(arg) if arg else fn())
        except Exception as exc:
            return _fail_human(state, f"{tool_name} failed: {exc}")
        if not envelope.get("ok"):
            # Order reads are load-bearing; knowledge reads are not.
            if tool_name in ("get_order", "get_order_items", "get_order_status"):
                return _fail_human(state, f"{tool_name} failed")
        if tool_name == "get_order" and envelope.get("ok"):
            order = envelope.get("order", {})
            oc = dict(state.get("order_context") or {})
            oc.update({"total_paise": order.get("total_paise"), "status": order.get("status")})
            delta["order_context"] = oc
    return delta


def check_policy(state: dict, tools: dict, llm=None) -> dict:
    """Deterministic policy gate. LLM never invents eligibility."""
    if state.get("decision") in ("ask_customer", "answered", "needs_human"):
        return {}
    workflow = state.get("workflow", "")
    if workflow not in ACTION_WORKFLOWS:
        return {}
    check_tool = WORKFLOW_CHECK_TOOL[workflow]
    fn = tools.get(check_tool)
    if fn is None:
        return _fail_human(state, f"{check_tool} unavailable")
    order_id = state.get("order_id")
    if not order_id:
        return {"decision": "ask_customer",
                "resolution": "Could you share the order number this is about?"}
    check = _trace(state, check_tool, fn(order_id))
    if not check.get("ok"):
        return _fail_human(state, f"{check_tool} failed")
    delta: dict[str, Any] = {
        "policy_context": {
            "action": workflow,
            "eligible": check.get("eligible"),
            "reasons": check.get("reasons", []),
        }
    }
    if not check.get("eligible"):
        reasons = "; ".join(check.get("reasons", []))
        delta["decision"] = "ineligible"
        delta["resolution"] = _draft(
            llm,
            f"I checked the policy for order {check.get('order_number')}: {reasons}. "
            "A support agent can review alternatives.",
            f"Explain ineligibility: {reasons}",
        )
    return delta


def propose(state: dict, tools: dict, llm=None) -> dict:
    """Propose action + decide HITL. Read-only intents answer directly."""
    if state.get("decision") in ("ask_customer", "answered", "needs_human", "ineligible"):
        return {}
    workflow = state.get("workflow", "")
    if workflow == "TRACKING":
        tracking = state.get("tracking_context") or state.get("_tracking", {})
        if not tracking:
            return _fail_human(state, "tracking context missing")
        steps = [s["label"] for s in tracking.get("timeline", []) if s.get("done")]
        template = (
            f"Order {tracking.get('order_number')} is {tracking.get('status')}. "
            f"Done so far: {', '.join(steps)}. "
            f"Estimated delivery: {tracking.get('estimated_delivery')}."
        )
        return {"decision": "answered",
                "resolution": _draft(llm, template, f"Relay tracking update: {template}")}
    if workflow not in ACTION_WORKFLOWS:
        return {}
    policy = state.get("policy_context") or {}
    if not policy.get("eligible"):
        return {}
    action_type = "REFUND" if workflow == "REFUND" else workflow
    amount = (state.get("order_context") or {}).get("total_paise", 0) if workflow == "REFUND" else 0
    required, reason = approval_policy.needs_approval(
        action_type=action_type,
        amount_paise=amount or 0,
        confidence=state.get("confidence", 1.0),
    )
    proposed = {
        "action_type": action_type,
        "order_id": state.get("order_id"),
        "reason": reason or "eligible under policy",
        "amount_paise": amount or None,
    }
    delta: dict[str, Any] = {"proposed_action": proposed}
    if required:
        delta["decision"] = "awaiting_approval"
        delta["approval_required"] = True
        delta["approval_status"] = None
        delta["resolution"] = _draft(
            llm,
            f"This needs a quick human approval ({reason}). I'll proceed as soon as support confirms.",
            f"Explain approval pause: {reason}",
        )
    return delta


def human_gate(state: dict, tools: dict, llm=None) -> dict:
    """HITL pause point. When approval is required and undecided, the graph
    ends here with WAITING_FOR_HUMAN; resume injects approval_status."""
    if not state.get("approval_required"):
        return {}
    status = state.get("approval_status")
    if status is None:
        return {"approval_status": "pending"}
    return {}


def execute(state: dict, tools: dict, llm=None) -> dict:
    """Execute approved or low-risk action (idempotent mutation key)."""
    if state.get("decision") in ("ask_customer", "answered", "needs_human", "ineligible"):
        return {}
    workflow = state.get("workflow", "")
    if workflow not in ACTION_WORKFLOWS:
        return {}
    if state.get("approval_required") and state.get("approval_status") != "approved":
        return {}
    mock_tool = WORKFLOW_MOCK_TOOL[workflow]
    fn = tools.get(mock_tool)
    if fn is None:
        return _fail_human(state, f"{mock_tool} unavailable")
    key = f"agent:{state['ticket_id']}:{workflow.lower()}"
    order_id = state.get("order_id")
    try:
        if workflow == "REFUND":
            amount = (state.get("order_context") or {}).get("total_paise", 0) or 0
            executed = _trace(state, mock_tool, fn(order_id, key, state["ticket_id"], amount))
        else:
            executed = _trace(state, mock_tool, fn(order_id, key, state["ticket_id"]))
    except Exception as exc:
        return _fail_human(state, f"{mock_tool} failed: {exc}")
    if not executed.get("ok"):
        return _fail_human(state, f"{mock_tool} failed: {executed.get('error')}")
    return {"action_result": executed.get("action")}


def verify(state: dict, tools: dict, llm=None) -> dict:
    """Independent verification: re-check eligibility must flip to ineligible."""
    if state.get("decision") in ("ask_customer", "answered", "needs_human", "ineligible"):
        return {}
    workflow = state.get("workflow", "")
    if workflow not in ACTION_WORKFLOWS:
        return {}
    if state.get("approval_required") and state.get("approval_status") != "approved":
        return {}
    if not state.get("action_result"):
        return {}
    check_tool = WORKFLOW_CHECK_TOOL[workflow]
    fn = tools.get(check_tool)
    if fn is None:
        return _fail_human(state, "verification tool unavailable")
    verify_envelope = _trace(state, check_tool, fn(state["order_id"]))
    if verify_envelope.get("ok") and verify_envelope.get("eligible"):
        return _fail_human(state, "verification failed after execution")
    return {"verification_result": {"ok": True, "tool": check_tool}}


def respond(state: dict, tools: dict, llm=None) -> dict:
    """Final customer-facing resolution (only after verify for actions)."""
    if state.get("decision") in ("ask_customer", "answered", "needs_human", "ineligible"):
        return {}
    if state.get("approval_required") and state.get("approval_status") != "approved":
        return {}
    workflow = state.get("workflow", "")
    templates = {
        "REFUND": "Your refund is done — it goes back to the original payment method.",
        "REPLACE": "Your replacement is arranged — it ships to your address.",
        "RETURN": "Your return is registered — keep the item packed for pickup.",
        "CANCELLATION": "Your order is cancelled — no money was captured.",
    }
    template = templates.get(workflow, "Done — let me know if you need anything else.")
    return {"decision": "resolved_ready",
            "resolution": _draft(llm, template, f"Confirm success: {template}")}
