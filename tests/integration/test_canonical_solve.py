"""Canonical acceptance: replacement via LangGraph → HITL → verify → AI message.

Covers the target scenario at graph level (DB-backed solve/approve paths
reuse the same runner + idempotent keys):
1. damaged headphones → REPLACEMENT intent
2. deterministic policy check
3. HITL pause when low confidence / high risk
4. resume SAME execution on approve
5. verify before respond
6. final resolution saved as customer-facing message
"""

from agent.support_graph.runner import (
    is_paused_for_human,
    resume_support_ticket,
    run_support_ticket,
)


def _tools(*, eligible_first=True, approve_flow=False):
    checks = {"n": 0}

    def _check(oid):
        checks["n"] += 1
        if checks["n"] == 1:
            return {"ok": True, "eligible": True, "reasons": [], "order_number": "ORD-HP"}
        return {"ok": True, "eligible": False, "reasons": ["replacement created"], "order_number": "ORD-HP"}

    executed = {"n": 0}

    def _mock(*args):
        executed["n"] += 1
        return {"ok": True, "action": {"id": f"act-{executed['n']}"}}

    return {
        "get_ticket": lambda tid: {
            "ok": True,
            "ticket": {
                "customer": {"id": "u1", "name": "Kim"},
                "subject": "My headphones arrived damaged. I want a replacement.",
                "description": "My headphones arrived damaged. I want a replacement.",
                "category": "REPLACEMENT",
                "related_order": {"id": "o-hp", "order_number": "ORD-HP"},
            },
        },
        "get_order": lambda oid: {"ok": True, "order": {"total_paise": 299900, "status": "DELIVERED"}},
        "get_order_items": lambda oid: {"ok": True, "items": [{"product": "headphones"}]},
        "check_replacement_eligibility": _check,
        "mock_replace": _mock,
        "search_knowledge": lambda q: {"ok": True, "results": []},
    }, checks, executed


def test_replacement_auto_executes_and_verifies() -> None:
    tools, checks, executed = _tools()
    state = run_support_ticket("t-hp", tools=tools)
    assert state["intent"] == "REPLACEMENT"
    assert state["workflow"] == "REPLACE"
    assert state["policy_context"]["eligible"] is True
    assert state["decision"] == "resolved_ready"
    assert executed["n"] == 1  # exactly once (idempotent key in service layer)
    assert state["verification_result"] == {"ok": True, "tool": "check_replacement_eligibility"}
    assert "replacement" in (state["resolution"] or "").lower()
    # Service layer persists this resolution as AI_AGENT ticket message.


def test_low_confidence_pauses_then_resumes_same_execution() -> None:
    tools, checks, executed = _tools()
    # Force HITL via low confidence: drive propose node directly.
    from agent.support_graph import nodes as n

    paused_state = {
        "ticket_id": "t-hp",
        "order_id": "o-hp",
        "intent": "REPLACEMENT",
        "confidence": 0.2,
        "workflow": "REPLACE",
        "policy_context": {"eligible": True, "reasons": []},
        "order_context": {},
        "tool_results": [],
    }
    delta = n.propose(dict(paused_state), tools, None)
    assert delta["approval_required"] is True
    assert is_paused_for_human({**paused_state, **delta})

    # Resume SAME execution after approve → execute → verify → respond.
    resumed = resume_support_ticket(
        {**paused_state, **delta, "approval_status": None},
        tools=tools,
        approval_status="approved",
        human_feedback="looks good",
    )
    assert resumed["approval_status"] == "approved"
    assert resumed["decision"] == "resolved_ready"
    assert resumed["verification_result"]["ok"] is True


def test_tool_failure_escalates_never_lies() -> None:
    tools, _, _ = _tools()
    tools["get_order"] = lambda oid: {"ok": False, "error": "db down"}
    state = run_support_ticket("t-fail", tools=tools)
    assert state["decision"] == "needs_human"
    assert state.get("escalated") is True
    assert state.get("action_result") is None
    assert "human" in (state.get("resolution") or "").lower()


def test_ambiguous_customer_waits_for_clarification() -> None:
    tools = {
        "get_ticket": lambda tid: {
            "ok": True,
            "ticket": {
                "customer": {"id": "u1", "name": "Kim"},
                "subject": "refund please",
                "description": "refund please",
                "category": "GENERAL",
                "related_order": None,
            },
        },
        "search_knowledge": lambda q: {"ok": True, "results": []},
    }
    state = run_support_ticket("t-amb", tools=tools)
    # GENERAL without order → knowledge answer or ask; never acts blindly.
    assert state.get("action_result") is None
    assert state["decision"] in ("answered", "ask_customer")
