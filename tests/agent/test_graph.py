"""Graph skeleton: topology, compilation, and stub paths (Phase 12).

Stub services drive every edge, so these tests run the real compiled
graph end to end with canned states — the manual "print the path" check,
as an assertion. `understand`/`contract` call services since Phase 13,
so fakes pin their behavior from task-text markers.
"""

import pytest

from agent.contract.models import Contract
from agent.graph.builder import NODE_NAMES, build_graph
from agent.llm.schemas import Interpretation, NextAction
from agent.runtime import wiring


class _FakeUnderstanding:
    """Interpretation from task-text markers (no LLM)."""

    def interpret(self, task_text):
        """Marker-driven proposal: impossible/cancel steer the contract."""
        text = task_text.lower()
        return Interpretation(
            summary=task_text[:80],
            goal=task_text[:80],
            requested_effects=[] if "impossible" in text else ["ticket.note"],
            mentioned_codes=[],
            mentioned_names=[],
            ambiguities=[],
            unsupported="impossible" in text,
        )


class _FakeContracts:
    """Contracts from task-text markers (no gateway, no database)."""

    def build_contract(self, task_id, task_text):
        text = task_text.lower()
        if "impossible" in text:
            status = "unsupported"
        elif "cancel" in text:
            status = "ambiguous"
        else:
            status = "ok"
        return Contract(
            task_id=task_id,
            goal=task_text[:80],
            effects=[],
            capabilities=["read"],
            ambiguity=[] if status == "ok" else [status],
            status=status,
        )


class _FakePlanning:
    """One canned observe step (topology only, no LLM)."""

    def create_plan(self, contract):
        """A fixed step over a read tool."""
        _ = contract
        return [{"step": "look", "tool": "browser_observe", "purpose": "stub"}]


class _FakeDecision:
    """Always propose a harmless observe (topology only, no LLM)."""

    def next_action(self, *args, **kwargs):
        """Ignore context; the canned action always validates."""
        _ = (args, kwargs)
        return NextAction(tool="browser_observe", params={}, rationale="stub")


class _FakeValidation:
    """Accept everything, reserve nothing (topology only, no database)."""

    def check_and_reserve(self, run_id, action, contract, validation_failures=0):
        """Mirror the service shape without side effects."""
        _ = (run_id, action, contract, validation_failures)
        return {
            "validation_status": "ok",
            "validation_error": "",
            "validation_failures": 0,
        }


class _FakePolicy:
    """Marker-driven verdicts (topology only, no facts, no database)."""

    def check_and_persist(self, task_id, run_id, action, contract, facts):
        """'refund everything' blocks; everything else allows."""
        _ = (task_id, run_id, action, facts)
        if "refund everything" in contract.goal:
            return _PolicyResult("block", "P-REF-004", "stub")
        return _PolicyResult()


class _PolicyResult:
    def __init__(self, outcome="allow", rule_id="P-NOTE-001", reason="stub", token=""):
        self.outcome = outcome
        self.rule_id = rule_id
        self.reason = reason
        self.token = token


class _FakeExecution:
    """Canned tool success (topology only, no journal, no gateway)."""

    def execute(self, task_id, run_id, action, policy_decision_id=None):
        """Mirror the service shape without side effects."""
        _ = (task_id, run_id, action, policy_decision_id)
        return _ExecResult()


class _ExecResult:
    action_id = "a1"
    mutation_key = "k1"

    def to_result_dict(self):
        """A successful observation payload for the fake observer."""
        return {"ok": True, "payload": {}, "error": "", "mutated": False}


class _FakeObservation:
    """Always done (topology only, no memory, no database)."""

    def observe(self, task_id, run_id, action, result):
        """Mirror the service shape without side effects."""
        _ = (task_id, run_id, action, result)
        return _ObsResult()


class _ObsResult:
    status = "effects_done"
    observation = {}


class _FakeFinalization:
    """Terminal mapping only (pure; safe for topology tests)."""

    def status(self, state):
        """Delegate to the real pure mapping (no persistence)."""
        from agent.services.finalization_service import final_status

        return final_status(state)


class _EmptyFacts:
    """No facts needed: the fake policy ignores them."""


class _FakeVerifier:
    """No database: snapshot is a no-op, verify always proves (topology only)."""

    def snapshot_before(self, contract, run_id):
        """Pretend the before-snapshot persisted."""
        _ = (contract, run_id)
        return {}

    def verify(self, contract, run_id):
        """Always proved; red-team coverage lives in tests/verifier."""
        _ = (contract, run_id)
        return {"verdict": "verified", "invariants": [], "diff": {}}


@pytest.fixture(autouse=True)
def _fake_wiring(monkeypatch):
    """Pin Phase 13/14 services to marker-driven fakes for topology tests."""
    monkeypatch.setattr(wiring, "understanding_service", lambda: _FakeUnderstanding())
    monkeypatch.setattr(wiring, "contract_service", lambda: _FakeContracts())
    monkeypatch.setattr(wiring, "planning_service", lambda: _FakePlanning())
    monkeypatch.setattr(wiring, "decision_service", lambda: _FakeDecision())
    monkeypatch.setattr(wiring, "validation_service", lambda: _FakeValidation())
    monkeypatch.setattr(wiring, "policy_service", lambda: _FakePolicy())
    monkeypatch.setattr(wiring, "execution_service", lambda: _FakeExecution())
    monkeypatch.setattr(wiring, "observation_service", lambda: _FakeObservation())
    monkeypatch.setattr(wiring, "finalization_service", lambda: _FakeFinalization())
    monkeypatch.setattr(wiring, "verifier_adapter", lambda: _FakeVerifier())
    monkeypatch.setattr("agent.nodes.policy_check.gather_facts", lambda *args: _EmptyFacts())


def _path(graph, state):
    """Node names visited by one run, in order."""
    visited = []
    for chunk in graph.stream(state, stream_mode="updates"):
        visited.extend(chunk.keys())
    return visited


def _state(task_id, task_text, **overrides):
    return {"task_id": task_id, "run_id": "r1", "task_text": task_text, **overrides}


def test_all_fifteen_nodes_registered():
    """The skeleton exposes every §13 node (services attach later)."""
    assert len(NODE_NAMES) == 15
    assert set(build_graph().get_graph().nodes) >= set(NODE_NAMES)


def test_unsupported_contract_path():
    """understand → contract → finalize(INCONCLUSIVE)."""
    graph = build_graph()
    state = _state("t1", "do the impossible")
    assert _path(graph, state) == ["understand", "contract", "finalize"]
    assert graph.invoke(state)["status"] == "inconclusive"


def test_happy_stub_path_to_verified():
    """Full spine: plan → act → observe(done) → verify → succeed."""
    graph = build_graph()
    state = _state("t2", "replace the damaged laptop", observation_status="effects_done")
    assert _path(graph, state) == [
        "understand",
        "contract",
        "plan",
        "decide",
        "validate",
        "policy_check",
        "execute",
        "observe",
        "verify",
        "finalize",
    ]
    assert graph.invoke(state)["status"] == "succeeded"


def test_blocked_policy_path():
    """BLOCK ends without touching execute or observe."""
    graph = build_graph()
    state = _state(
        "t3",
        "refund everything",
        policy_decision={"outcome": "block", "rule_id": "P-REF-004", "reason": "stub"},
    )
    visited = _path(graph, state)
    assert visited == [
        "understand",
        "contract",
        "plan",
        "decide",
        "validate",
        "policy_check",
        "finalize",
    ]
    assert "execute" not in visited


def test_parked_clarification_ends_graph():
    """Ambiguous contracts park: the graph ends, the task does not."""
    graph = build_graph()
    state = _state("t4", "cancel it")
    assert _path(graph, state) == ["understand", "contract", "clarification"]
    assert graph.invoke(state).get("status") != "succeeded"
