"""Planning + decision services: shape checks and bounded correction."""

import pytest

from agent.contract.models import Contract
from agent.llm.schemas import NextAction, PlanProposal, PlanStep
from agent.services.decision_service import DecisionService
from agent.services.planning_service import PlanningError, PlanningService


def _contract(**overrides):
    base = {
        "task_id": "t1",
        "goal": "replace the item",
        "customer_id": "c-101",
        "order_id": "o-1942",
        "ticket_id": "t-101",
        "effects": [],
        "capabilities": ["read", "read.fallback", "probe", "browser", "replacement.create"],
        "status": "ok",
    }
    base.update(overrides)
    return Contract.model_validate(base)


class _FakeLLM:
    """Canned proposal (records the user brief for assertion)."""

    def __init__(self, proposal):
        self._proposal = proposal
        self.calls = 0
        self.last_user = ""

    def propose(self, model_cls, system, user):
        """Return the preset, checking the schema asked for."""
        self.calls += 1
        self.last_user = user
        assert model_cls in (PlanProposal, NextAction)
        _ = system
        return self._proposal


def _plan_proposal():
    return PlanProposal(
        steps=[
            PlanStep(step="find-order", tool="search_order", purpose="bind IDs"),
            PlanStep(step="check-policy", tool="get_policy", purpose="scope"),
            PlanStep(step="open-form", tool="browser_open", purpose="act"),
            PlanStep(step="verify", tool="inspect_state", purpose="prove"),
        ],
        notes="reads first",
    )


def test_plan_preserves_phases_in_order():
    """Find-order, check-policy, act, verify survive shaping intact."""
    service = PlanningService(_FakeLLM(_plan_proposal()))
    steps = service.create_plan(_contract())
    assert [step["tool"] for step in steps] == [
        "search_order",
        "get_policy",
        "browser_open",
        "inspect_state",
    ]


def test_plan_rejects_unknown_tools():
    """Hallucinated plan tools are a planning error, not a runtime retry."""
    bad = PlanProposal(steps=[PlanStep(step="x", tool="teleport", purpose="y")], notes="")
    with pytest.raises(PlanningError, match="unregistered tools"):
        PlanningService(_FakeLLM(bad)).create_plan(_contract())


def test_plan_rejects_non_ok_contracts():
    """Ambiguous contracts never produce steps."""
    with pytest.raises(PlanningError, match="ambiguous"):
        PlanningService(_FakeLLM(_plan_proposal())).create_plan(_contract(status="ambiguous"))


def test_decision_returns_proposal():
    """The next action carries tool, params, and rationale."""
    action = NextAction(tool="search_order", params={"customer_id": "c-101"}, rationale="bind")
    service = DecisionService(_FakeLLM(action))
    result = service.next_action(_contract(), [], 0, [], {})
    assert result.tool == "search_order"
    assert result.params["customer_id"] == "c-101"


def test_decision_feedback_loop_terminates():
    """Exhausted corrections fall back to observe without another LLM call."""
    llm = _FakeLLM(NextAction(tool="browser_click", params={"ref": "e1"}, rationale="bad"))
    service = DecisionService(llm)
    result = service.next_action(
        _contract(), [], 0, [], {}, validation_error="unknown tool", validation_failures=3
    )
    assert result.tool == "browser_observe"
    assert llm.calls == 0


def test_decision_brief_carries_correction():
    """The validator's error reaches the next proposal verbatim."""
    llm = _FakeLLM(NextAction(tool="browser_observe", params={}, rationale="ok"))
    DecisionService(llm).next_action(
        _contract(),
        [],
        0,
        [],
        {},
        validation_error="binding: order_id wrong",
        validation_failures=1,
    )
    assert "binding: order_id wrong" in llm.last_user


def test_decision_brief_grounds_in_plan_and_memory():
    """Plan position, memory, and observation all reach the decider."""
    llm = _FakeLLM(NextAction(tool="browser_observe", params={}, rationale="ok"))
    plan = [{"step": "find", "tool": "search_order", "purpose": "bind"}]
    DecisionService(llm).next_action(_contract(), plan, 0, [{"key": "k"}], {"url": "/ops"}, "")
    assert "find" in llm.last_user and "k" in llm.last_user
