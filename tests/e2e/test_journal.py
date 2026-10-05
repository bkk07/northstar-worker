"""Phase 16: journal-first execution against live Postgres (no LLM).

A stub gateway stands in for the MCP servers; every journal, attempt,
memory, and checkpoint row is real. Proves: STARTED rows exist before
the tool runs, validate→execute handoff reuses the reserved row,
attempts close with outcomes, and observation writes memory.
"""

from uuid import UUID

from sqlalchemy import text

from agent.contract.models import Contract
from agent.ports.clock import SystemClock
from agent.repositories.task_repository import TaskRepository
from agent.runtime.runner import _terminal_for
from agent.services.execution_service import ExecutionService
from agent.services.finalization_service import final_status
from agent.services.observation_service import ObservationService
from agent.services.validation_service import ValidationService
from database import session as session_factory


class _StubGateway:
    """Tool calls that assert journal-first, then succeed."""

    def __init__(self, session, run_id):
        self._session = session
        self._run_id = run_id
        self.calls = []

    def browser_observe(self, task_id):
        self.calls.append("browser_observe")
        assert self._started_row() is not None, "STARTED row must predate the tool call"
        return {"url": "http://x/ops", "title": "ops", "refs": {"e1": {}}}

    def browser_submit(self, task_id, ref, mutation_key, token, params):
        self.calls.append("browser_submit")
        row = self._started_row()
        assert row is not None and row[0] == mutation_key, "key assigned before commit"
        return {
            "ok": True,
            "status": 201,
            "effect": "replacement.create",
            "mutation_key": mutation_key,
        }

    def _started_row(self):
        return self._session.execute(
            text(
                "SELECT mutation_key, status FROM worker.actions "
                "WHERE run_id = :rid ORDER BY seq DESC LIMIT 1"
            ),
            {"rid": self._run_id},
        ).first()


def _task_and_run(session, created):
    repo = TaskRepository(session)
    task = repo.create_task("replace the damaged laptop", "explicit", "e2e-journal")
    run = repo.create_run(task.id, "e2e", SystemClock().now())
    session.commit()
    created.append(task.id)
    return task, run


def _runner_factory():
    """One short-lived `ns_runner` session (mirrors the wiring factory)."""
    return session_factory.session_for(session_factory.runner_engine())


def _contract(task_id):
    return Contract(
        task_id=str(task_id),
        goal="replace the damaged laptop",
        effects=[],
        capabilities=["browser"],
        status="ok",
    )


def test_journal_rows_are_complete(runner_session):
    """STARTED → attempt → done, with the validate handoff intact."""
    session, created = runner_session
    task, run = _task_and_run(session, created)
    gateway = _StubGateway(session, run.id)
    factory = _runner_factory
    validation = ValidationService(factory)
    execution = ExecutionService(factory, gateway, SystemClock())
    contract = _contract(task.id)

    action = {"tool": "browser_observe", "params": {}, "rationale": "look"}
    assert validation.check_and_reserve(str(run.id), action, contract)["validation_status"] == "ok"
    result = execution.execute(str(task.id), str(run.id), action)
    assert result.ok is True
    assert gateway.calls == ["browser_observe"]

    rows = session.execute(
        text(
            "SELECT seq, tool, status, mutation_key FROM worker.actions "
            "WHERE run_id = :rid ORDER BY seq"
        ),
        {"rid": run.id},
    ).all()
    assert len(rows) == 1, "validate reserves once; execute reuses the row"
    assert rows[0][1] == "browser_observe" and rows[0][2] == "done"
    assert rows[0][3] == result.mutation_key and rows[0][3]

    attempts = session.execute(
        text(
            "SELECT outcome FROM worker.action_attempts WHERE action_id IN "
            "(SELECT id FROM worker.actions WHERE run_id = :rid)"
        ),
        {"rid": run.id},
    ).all()
    assert [row[0] for row in attempts] == ["ok"]


def test_submit_commit_journals_mutation(runner_session):
    """Submits journal their idempotency key; observe routes effects_done."""
    session, created = runner_session
    task, run = _task_and_run(session, created)
    gateway = _StubGateway(session, run.id)
    factory = _runner_factory
    execution = ExecutionService(factory, gateway, SystemClock())
    observation = ObservationService(factory)

    action = {
        "tool": "browser_submit",
        "params": {"ref": "e9", "token": "tok", "effect": "replacement.create"},
        "rationale": "commit",
    }
    result = execution.execute(str(task.id), str(run.id), action)
    assert result.ok and result.mutated
    verdict = observation.observe(str(task.id), str(run.id), action, result.to_result_dict())
    assert verdict.status == "effects_done"

    key = session.execute(
        text("SELECT mutation_key FROM worker.actions WHERE run_id = :rid"),
        {"rid": run.id},
    ).scalar()
    assert key == result.mutation_key
    memory = session.execute(
        text("SELECT source_type, trust FROM worker.memory_items WHERE run_id = :rid"),
        {"rid": run.id},
    ).all()
    assert ("browser", "untrusted") in memory


def test_failed_tool_journals_and_routes_failure(runner_session):
    """Transport errors close attempts as failed and route to classify."""

    class _Boom(_StubGateway):
        def browser_click(self, task_id, ref):
            raise RuntimeError("transport down")

    session, created = runner_session
    task, run = _task_and_run(session, created)
    factory = _runner_factory
    execution = ExecutionService(factory, _Boom(session, run.id), SystemClock())
    observation = ObservationService(factory)

    action = {"tool": "browser_click", "params": {"ref": "e1"}, "rationale": "x"}
    result = execution.execute(str(task.id), str(run.id), action)
    assert result.ok is False and result.error == "transport down"
    verdict = observation.observe(str(task.id), str(run.id), action, result.to_result_dict())
    assert verdict.status == "failure"

    outcome, error = session.execute(
        text(
            "SELECT outcome, error_type FROM worker.action_attempts WHERE action_id IN "
            "(SELECT id FROM worker.actions WHERE run_id = :rid)"
        ),
        {"rid": run.id},
    ).first()
    assert outcome == "error" and error == "network_error"
    status = session.execute(
        text("SELECT status FROM worker.actions WHERE run_id = :rid"), {"rid": run.id}
    ).scalar()
    assert status == "failed"


def test_terminal_mapping_covers_parked_runs():
    """Approval-pending graphs park; they never finalize inconclusive."""
    assert _terminal_for({"approval_status": "pending"}).value == "waiting_for_approval"
    assert _terminal_for({"clarification_status": "pending"}).value == ("waiting_for_clarification")
    assert final_status({"verification": {"verdict": "verified"}}) == "succeeded"
    assert UUID(int=0) is not None
