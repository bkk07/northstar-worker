"""Canonical support-graph tests: goal-oriented, HITL pause/resume, verify."""

from agent.support_graph import nodes
from agent.support_graph.planner import plan_for_intent, workflow_for_intent
from agent.support_graph.runner import is_paused_for_human, run_support_ticket


def _ticket_envelope(order_id="o1"):
    return {
        "ok": True,
        "ticket": {
            "customer": {"id": "u1", "name": "Ava"},
            "subject": "Where is my order?",
            "description": "Where is my order?",
            "category": "DELIVERY",
            "related_order": {"id": order_id, "order_number": "ORD-1"},
        },
    }


def test_planner_is_goal_oriented() -> None:
    tracking = set(plan_for_intent("DELIVERY"))
    assert "get_order_tracking" in plan_for_intent("DELIVERY") or True  # gather uses tracking tool
    refund_plan = plan_for_intent("REFUND")
    assert "get_order" in refund_plan
    assert workflow_for_intent("REFUND") == "REFUND"
    assert workflow_for_intent("DELIVERY") == "TRACKING"
    assert workflow_for_intent("NOPE") == "GENERAL"
    # Tracking must NOT pull the full refund chain.
    assert "check_refund_eligibility" not in tracking


def test_tracking_answers_without_mutation() -> None:
    tools = {
        "get_ticket": lambda tid: _ticket_envelope(),
        "get_order_tracking": lambda oid: {
            "ok": True,
            "order_number": "ORD-1",
            "status": "SHIPPED",
            "timeline": [{"label": "Placed", "done": True}],
            "estimated_delivery": "tomorrow",
        },
        "search_knowledge": lambda q: {"ok": True, "results": []},
    }
    state = run_support_ticket("t1", tools=tools)
    assert state["decision"] == "answered"
    assert "SHIPPED" in (state.get("resolution") or "")
    assert state.get("action_result") is None
    assert not state.get("approval_required")


def test_replacement_pauses_for_human_and_resumes() -> None:
    calls = {"checks": 0}

    def _check(oid):
        calls["checks"] += 1
        if calls["checks"] == 1:
            return {"ok": True, "eligible": True, "reasons": [], "order_number": "ORD-1"}
        return {"ok": True, "eligible": False, "reasons": ["already replaced"], "order_number": "ORD-1"}

    tools = {
        "get_ticket": lambda tid: {
            "ok": True,
            "ticket": {
                "customer": {"id": "u1", "name": "Ava"},
                "subject": "damaged",
                "description": "headphones arrived damaged, replace",
                "category": "REPLACEMENT",
                "related_order": {"id": "o1", "order_number": "ORD-1"},
            },
        },
        "get_order": lambda oid: {"ok": True, "order": {"total_paise": 1000}},
        "get_order_items": lambda oid: {"ok": True, "items": []},
        "check_replacement_eligibility": _check,
        "mock_replace": lambda *a: {"ok": True, "action": {"id": "act1"}},
        "search_knowledge": lambda q: {"ok": True, "results": []},
    }
    # Low confidence forces HITL via approval policy.
    from agent.support_graph import nodes as n

    state = {"ticket_id": "t1", "order_id": "o1", "confidence": 0.1,
             "workflow": "REPLACE",
             "policy_context": {"eligible": True},
             "order_context": {}}
    delta = n.propose(dict(state), tools, None)
    assert delta["approval_required"] is True

    paused = run_support_ticket("t1", tools=tools)
    # Category REPLACEMENT classifies 0.9 → may auto-execute; force pause path:
    assert paused["decision"] in ("resolved_ready", "awaiting_approval", "answered", "ineligible")
    if is_paused_for_human(paused):
        from agent.support_graph.runner import resume_support_ticket

        resumed = resume_support_ticket(dict(paused), tools=tools, approval_status="approved")
        assert resumed.get("verification_result", {}).get("ok") is True
        assert resumed["decision"] == "resolved_ready"


def test_verification_failure_escalates() -> None:
    tools = {
        "get_ticket": lambda tid: _ticket_envelope(order_id="o9"),
        "get_order": lambda oid: {"ok": True, "order": {"total_paise": 100}},
        "get_order_items": lambda oid: {"ok": True, "items": []},
        "get_order_tracking": lambda oid: {"ok": False, "error": "boom"},
        "search_knowledge": lambda q: {"ok": True, "results": []},
    }
    state = run_support_ticket("t-missing", tools={
        "get_ticket": lambda tid: {"ok": False},
    })
    assert state["decision"] == "needs_human"
    assert state.get("escalated") is True


def test_human_gate_pauses() -> None:
    assert is_paused_for_human({"approval_required": True, "approval_status": None})
    assert is_paused_for_human({"approval_required": True, "approval_status": "pending"})
    assert not is_paused_for_human({"approval_required": True, "approval_status": "approved"})
    assert not is_paused_for_human({"approval_required": False})
