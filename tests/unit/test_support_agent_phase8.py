"""Phase 8 support-agent unit tests (no model calls, no DB, no docker).

Everything LLM-shaped uses `FakeLLM`; every tool-shaped dependency uses
in-memory fakes. Nothing here may open a socket: the suite must stay fast.
"""

import pytest

from agent.llm.client import LLMError, config_from_env
from agent.support import approval as approval_policy
from agent.support import workflows
from agent.support.classifier import classify, mock_classify
from agent.support.runner import run_ticket
from agent.support.state import fresh_state


class FakeLLM:
    """Canned proposals/replies; records use (never a model)."""

    def __init__(self, intent="REFUND", confidence=0.95, reply="Canned reply."):
        self.intent = intent
        self.confidence = confidence
        self.reply = reply
        self.propose_calls = 0
        self.complete_calls = 0

    def propose(self, model_cls, system, user):
        self.propose_calls += 1
        return model_cls(intent=self.intent, confidence=self.confidence)

    def complete(self, system, user):
        self.complete_calls += 1
        return self.reply


def _ticket_envelope(order_id="o1"):
    return {
        "ok": True,
        "ticket": {
            "id": "t1",
            "subject": "Screen arrived cracked",
            "description": "The screen arrived cracked, please refund.",
            "category": "REFUND",
            "customer": {"id": "u1", "name": "Jane"},
            "related_order": {"id": order_id, "order_number": "ORD-1"},
        },
    }


def _refund_tools(*, total=129900, eligible_first=True, fail_check=False):
    calls = {"mock": [], "checks": 0}

    def check(order_id):
        calls["checks"] += 1
        if fail_check:
            return {"ok": False, "code": "X", "error": "boom"}
        eligible = eligible_first if calls["checks"] == 1 else False
        return {
            "ok": True,
            "eligible": eligible,
            "reasons": [] if eligible else ["already refunded"],
            "order_number": "ORD-1",
        }

    def get_order(order_id):
        return {"ok": True, "order": {"total_paise": total}}

    def mock(order_id, key, ticket_id, amount):
        calls["mock"].append((order_id, key, ticket_id, amount))
        return {"ok": True, "action": {"id": "a1", "status": "DONE"}}

    return calls, {
        "check_refund_eligibility": check,
        "get_order": get_order,
        "mock_refund": mock,
    }


def test_groq_config_wins_when_key_set() -> None:
    config = config_from_env({"GROQ_API_KEY": "gsk-test"})
    assert config.model == "llama-3.3-70b-versatile"
    assert config.base_url == "https://api.groq.com/openai/v1"
    assert config.strict_schema is False
    assert config.reasoning_effort == ""


def test_groq_explicit_overrides() -> None:
    config = config_from_env({"GROQ_API_KEY": "gsk-test", "GROQ_MODEL": "llama-x"})
    assert config.model == "llama-x"


def test_missing_keys_raise() -> None:
    with pytest.raises(LLMError):
        config_from_env({})


def test_mock_classifier_paths() -> None:
    assert mock_classify("s", "d", "REFUND").intent == "REFUND"
    assert mock_classify("Where is my parcel?", "tracking help", "GENERAL").intent == "ORDER_STATUS"
    assert mock_classify("Hello", "just saying hi", "GENERAL").intent == "GENERAL_QUERY"


def test_classify_uses_live_llm_when_given() -> None:
    llm = FakeLLM(intent="PAYMENT", confidence=0.8)
    verdict = classify("s", "d", "GENERAL", llm)
    assert verdict.intent == "PAYMENT"
    assert llm.propose_calls == 1


def test_approval_matrix() -> None:
    required, reason = approval_policy.needs_approval(
        action_type="REFUND", amount_paise=600_000, confidence=0.95
    )
    assert required and "cap" in reason
    required, _ = approval_policy.needs_approval(
        action_type="REFUND", amount_paise=100, confidence=0.5
    )
    assert required
    required, _ = approval_policy.needs_approval(
        action_type="RETURN", amount_paise=0, confidence=0.9
    )
    assert not required
    required, _ = approval_policy.needs_approval(
        action_type=None, confidence=0.9, human_requested=True
    )
    assert required


def test_refund_happy_path() -> None:
    calls, tools = _refund_tools()
    state = fresh_state("t1")
    out = workflows.refund_workflow(state, "o1", 0.95, tools)
    assert out["decision"] == "resolved_ready"
    assert out["action_result"] == {"id": "a1", "status": "DONE"}
    [(order_id, key, ticket_id, amount)] = calls["mock"]
    assert key == "agent:t1:refund" and amount == 129900
    assert out["resolution"].startswith("Your refund is done")


def test_refund_ineligible_acts_nothing() -> None:
    calls, tools = _refund_tools(eligible_first=False)
    state = fresh_state("t1")
    out = workflows.refund_workflow(state, "o1", 0.95, tools)
    assert out["decision"] == "ineligible"
    assert calls["mock"] == []


def test_refund_high_value_pauses_for_approval() -> None:
    calls, tools = _refund_tools(total=600_000)
    state = fresh_state("t1")
    out = workflows.refund_workflow(state, "o1", 0.95, tools, llm=FakeLLM())
    assert out["decision"] == "awaiting_approval"
    assert out["approval_required"] is True
    assert calls["mock"] == []
    assert out["proposed_action"]["action_type"] == "REFUND"


def test_tool_failure_routes_to_human() -> None:
    _, tools = _refund_tools(fail_check=True)
    state = fresh_state("t1")
    out = workflows.refund_workflow(state, "o1", 0.95, tools)
    assert out["decision"] == "needs_human"
    assert out["approval_required"] is True


def test_tracking_and_general_answers() -> None:
    tools = {
        "get_order_tracking": lambda oid: {
            "ok": True,
            "order_number": "ORD-1",
            "status": "SHIPPED",
            "timeline": [{"label": "Shipped", "done": True}],
            "estimated_delivery": "tomorrow",
        },
        "search_knowledge": lambda q: {"ok": True, "results": []},
    }
    tracked = workflows.tracking_workflow(fresh_state("t1"), "o1", tools)
    assert tracked["decision"] == "answered" and "SHIPPED" in tracked["resolution"]
    general = workflows.general_workflow(fresh_state("t1"), "hello", tools)
    assert general["decision"] == "answered"


def test_runner_end_to_end_with_fakes(monkeypatch) -> None:
    calls, tools = _refund_tools()
    tools["get_ticket"] = lambda tid: _ticket_envelope()
    posted = []
    monkeypatch.setattr(
        "agent.support.runner.ticket_tools.add_ticket_message",
        lambda tid, msg, sender="AI_AGENT": posted.append((tid, sender, msg)),
    )
    state = run_ticket("t1", tools=tools)
    assert state["intent"] == "REFUND"
    assert state["decision"] == "resolved_ready"
    assert calls["mock"] and posted
    assert posted[0][1] == "AI_AGENT"


def test_runner_missing_ticket() -> None:
    state = run_ticket("missing", tools={"get_ticket": lambda tid: {"ok": False}})
    assert state["decision"] == "needs_human"


def test_runner_asks_for_order_number(monkeypatch) -> None:
    envelope = _ticket_envelope(order_id=None)
    envelope["ticket"]["related_order"] = None
    tools = {"get_ticket": lambda tid: envelope}
    monkeypatch.setattr(
        "agent.support.runner.ticket_tools.add_ticket_message",
        lambda tid, msg, sender="AI_AGENT": None,
    )
    state = run_ticket("t1", tools=tools)
    assert state["decision"] == "ask_customer"
