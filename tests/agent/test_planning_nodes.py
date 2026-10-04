"""Plan/decide/validate nodes + action rows (Phase 14).

Node bodies delegate to wiring factories (monkeypatched here); the
validation service is exercised for real against live Postgres to prove
`actions` rows are reserved exactly once per accepted proposal.
"""

import uuid

from agent.contract.models import Contract
from agent.graph.state import WorkerState
from agent.llm.schemas import NextAction
from agent.nodes import decide as decide_node
from agent.nodes import plan as plan_node
from agent.nodes import validate as validate_node
from agent.repositories.action_repository import ActionRepository
from agent.runtime import wiring
from agent.services.validation_service import ValidationService
from database import session as session_factory
from database.models.worker.action import Action
from database.models.worker.task import Task, TaskRun


def _contract():
    return Contract(
        task_id="t1",
        goal="replace the item",
        customer_id="c-101",
        order_id="o-1942",
        ticket_id="t-101",
        effects=[],
        capabilities=["read", "read.fallback", "probe", "browser"],
        status="ok",
    )


def test_plan_node_stores_steps(monkeypatch):
    """Steps and a zero cursor land in checkpoint state."""

    class _Planning:
        def create_plan(self, contract):
            assert contract.task_id == "t1"
            return [{"step": "s", "tool": "browser_observe", "purpose": "p"}]

    monkeypatch.setattr(wiring, "planning_service", lambda: _Planning())
    delta = plan_node.plan(
        WorkerState(task_id="t1", run_id="r1", task_text="x", contract=_contract().model_dump())
    )
    assert delta["plan"][0]["tool"] == "browser_observe"
    assert delta["cursor"] == 0


def test_decide_node_stores_action(monkeypatch):
    """The chosen action lands in state for validation."""

    class _Decision:
        def next_action(self, *args, **kwargs):
            return NextAction(tool="browser_observe", params={}, rationale="stub")

    monkeypatch.setattr(wiring, "decision_service", lambda: _Decision())
    delta = decide_node.decide(
        WorkerState(task_id="t1", run_id="r1", task_text="x", contract=_contract().model_dump())
    )
    assert delta["last_action"]["tool"] == "browser_observe"


def test_validate_node_accepts_and_counts(monkeypatch):
    """Accepted proposals reset the failure count."""

    class _Validation:
        def check_and_reserve(self, run_id, action, contract, failures=0):
            assert (run_id, failures) == ("r1", 2)
            _ = (action, contract)
            return {"validation_status": "ok", "validation_error": "", "validation_failures": 0}

    monkeypatch.setattr(wiring, "validation_service", lambda: _Validation())
    delta = validate_node.validate(
        WorkerState(
            task_id="t1",
            run_id="r1",
            task_text="x",
            contract=_contract().model_dump(),
            last_action={"tool": "browser_observe", "params": {}, "rationale": "s"},
            validation_failures=2,
        )
    )
    assert delta["validation_status"] == "ok"
    assert delta["validation_failures"] == 0


def test_validation_service_reserves_rows():
    """One accepted proposal reserves exactly one `proposed` row."""
    engine = session_factory.admin_engine()
    setup = session_factory.session_for(engine)
    task = Task(
        id=uuid.uuid4(),
        text="x",
        mode="explicit",
        status="running",
        current_state="running",
        created_by="phase14-test",
    )
    run = TaskRun(id=uuid.uuid4(), task_id=task.id, attempt=1)
    setup.add_all([task, run])
    setup.commit()
    run_key = str(run.id)
    sessions = lambda: session_factory.session_for(engine)  # noqa: E731
    try:
        service = ValidationService(sessions)
        action = {"tool": "browser_observe", "params": {}, "rationale": "look"}
        first = service.check_and_reserve(run_key, action, _contract())
        assert first["validation_status"] == "ok"
        second = service.check_and_reserve(run_key, action, _contract())
        assert second["validation_status"] == "ok"
        rows = ActionRepository(sessions()).list_by_run(run.id)
        sessions().close()
        assert [row.seq for row in rows] == [0, 1]
        assert all(row.status == "proposed" for row in rows)
        bad = service.check_and_reserve(
            run_key, {"tool": "nope", "params": {}, "rationale": "x"}, _contract()
        )
        assert bad["validation_status"] == "invalid"
        assert bad["validation_failures"] == 1
        assert "unknown tool" in bad["validation_error"]
    finally:
        cleanup = session_factory.session_for(engine)
        try:
            cleanup.query(Action).filter(Action.run_id == run.id).delete(synchronize_session=False)
            cleanup.query(TaskRun).filter(TaskRun.id == run.id).delete(synchronize_session=False)
            cleanup.query(Task).filter(Task.id == task.id).delete(synchronize_session=False)
            cleanup.commit()
        finally:
            cleanup.close()
        setup.close()
