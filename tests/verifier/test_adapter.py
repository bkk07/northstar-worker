"""Adapter round-trip against live Postgres (no LLM, no browser).

Proves the before-snapshot persists at contract lock, verify persists a
verdict row, and a run without a snapshot verifies INCONCLUSIVE.
"""

from agent.adapters.verifier_adapter import VerifierAdapter
from agent.ports.clock import SystemClock
from agent.repositories.task_repository import TaskRepository
from database import session as session_factory
from database.models.worker.evidence import Snapshot, VerificationResult


def _adapter():
    return VerifierAdapter(
        lambda: session_factory.session_for(session_factory.runner_engine()),
        lambda: session_factory.session_for(session_factory.verifier_engine()),
    )


def _task_and_run(session, created):
    repo = TaskRepository(session)
    task = repo.create_task("verify the replacement", "explicit", "verifier-test")
    run = repo.create_run(task.id, "verifier-test", SystemClock().now())
    session.commit()
    created.append(task.id)
    return task, run


def test_snapshot_before_persists_and_first_wins(runner_session):
    session, created = runner_session
    _, run = _task_and_run(session, created)
    adapter = _adapter()
    contract = {"snapshot_scope": {}}
    first = adapter.snapshot_before(contract, str(run.id))
    second = adapter.snapshot_before(contract, str(run.id))
    assert first == second
    rows = session.query(Snapshot).filter(Snapshot.run_id == run.id).all()
    assert len(rows) == 1 and rows[0].phase == "before"


def test_verify_persists_failed_when_nothing_moved(runner_session):
    session, created = runner_session
    _, run = _task_and_run(session, created)
    adapter = _adapter()
    contract = {
        "effects": [
            {
                "effect": "replacement.create",
                "params": {"order_id": "o", "order_item_id": "i", "ticket_id": "t"},
                "capability": "replacement.create",
            }
        ],
        "snapshot_scope": {},
    }
    adapter.snapshot_before(contract, str(run.id))
    outcome = adapter.verify(contract, str(run.id))
    assert outcome["verdict"] == "failed"
    assert any(not i["passed"] for i in outcome["invariants"])
    rows = session.query(VerificationResult).filter(VerificationResult.run_id == run.id).all()
    assert len(rows) == 1 and rows[0].verdict == "failed"


def test_verify_without_snapshot_is_inconclusive(runner_session):
    session, created = runner_session
    _, run = _task_and_run(session, created)
    outcome = _adapter().verify({"effects": []}, str(run.id))
    assert outcome["verdict"] == "inconclusive"
