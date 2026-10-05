"""Node bodies: understand stores the proposal, contract locks it (Phase 13).

Wiring factories are monkeypatched; the compiler and services are covered
in their own test files.
"""

from agent.contract.models import Contract
from agent.graph.state import WorkerState
from agent.llm.schemas import Interpretation
from agent.nodes import contract as contract_node
from agent.nodes import understand as understand_node
from agent.runtime import wiring


def _interpretation():
    return Interpretation(
        summary="s",
        goal="g",
        requested_effects=[],
        mentioned_codes=[],
        mentioned_names=[],
        ambiguities=[],
        unsupported=False,
    )


def test_understand_stores_interpretation(monkeypatch):
    """The proposal lands in state for the compiler (and the timeline)."""

    class _Understanding:
        def interpret(self, task_text):
            assert task_text == "Replace the laptop."
            return _interpretation()

    monkeypatch.setattr(wiring, "understanding_service", lambda: _Understanding())
    delta = understand_node.understand(
        WorkerState(task_id="t", run_id="r", task_text="Replace the laptop.")
    )
    assert delta["interpretation"]["goal"] == "g"
    assert delta["status"] == "running"


def test_contract_node_locks_status(monkeypatch):
    """The node persists the compiler result and exposes its status."""

    class _Contracts:
        def build_contract(self, task_id, task_text):
            assert (task_id, task_text) == ("t", "Replace.")
            return Contract(
                task_id=task_id,
                goal="g",
                status="ambiguous",
                ambiguity=["which customer?"],
            )

    monkeypatch.setattr(wiring, "contract_service", lambda: _Contracts())
    monkeypatch.setattr(wiring, "audit_emitter", lambda: _NullAudit())
    delta = contract_node.contract(WorkerState(task_id="t", run_id="r", task_text="Replace."))
    assert delta["contract_status"] == "ambiguous"
    assert delta["contract"]["ambiguity"] == ["which customer?"]


class _NullAudit:
    """Swallow node audit (unit scope: emission is covered by graph tests)."""

    def emit(self, *args, **kwargs):
        """No database in node unit tests."""
        _ = (args, kwargs)


def test_understanding_rejects_empty_text():
    """Empty tasks fail before any LLM call is spent."""
    import pytest

    from agent.services.understanding_service import UnderstandingService

    class _LLM:
        def propose(self, *args, **kwargs):
            raise AssertionError("must not be called")

    with pytest.raises(ValueError, match="empty task text"):
        UnderstandingService(_LLM()).interpret("   ")
