"""HITL park and resume across a runner restart (Phase 22, live Postgres).

A stub graph runs the real `human_approval` node: the first runner parks
the task WAITING_FOR_APPROVAL, the operator approves through the worker
API service, and a fresh runner instance resumes from the checkpoint
into an approved, token-carrying state. No LLM, no browser.
"""

import pytest
from sqlalchemy import text

from agent.nodes.human_approval import human_approval
from agent.ports.clock import SystemClock
from agent.repositories.task_repository import TaskRepository
from agent.runtime.runner import Runner
from app.schemas.worker.approvals import ApprovalDecide
from app.services.worker.approval_service import ApprovalService
from database import session as session_factory
from mcp_server.token_guard import verify_submit_token

SECRET = "test-secret"


@pytest.fixture(autouse=True)
def _secret(monkeypatch):
    """The node signs with the test secret (wiring reads the env)."""
    monkeypatch.setenv("POLICY_TOKEN_SECRET", SECRET)


class _ParkGraph:
    """One node per run: the real approval body, parked or resumed."""

    def stream(self, state, config=None, stream_mode=None):
        """Yield the node delta, then end (the runner parks the rest)."""
        _ = (config, stream_mode)
        yield {"human_approval": human_approval(dict(state))}


@pytest.fixture()
def task_id():
    """Throwaway pending task, cleaned up with its HITL rows."""
    engine = session_factory.admin_engine()
    session = session_factory.session_for(engine)
    repo = TaskRepository(session)
    task = repo.create_task("refund Rs. 35,000", "explicit", "phase22-e2e")
    session.commit()
    key = task.id
    session.close()
    try:
        yield key
    finally:
        cleanup = session_factory.session_for(engine)
        try:
            cleanup.execute(
                text("DELETE FROM worker.evidence WHERE task_id = :id"),
                {"id": str(key)},
            )
            cleanup.execute(
                text("DELETE FROM worker.approvals WHERE task_id = :id"),
                {"id": str(key)},
            )
            cleanup.execute(
                text(
                    "DELETE FROM worker.task_checkpoints WHERE run_id IN "
                    "(SELECT id FROM worker.task_runs WHERE task_id = :id)"
                ),
                {"id": str(key)},
            )
            cleanup.execute(
                text("DELETE FROM worker.audit_events WHERE task_id = :id"),
                {"id": str(key)},
            )
            cleanup.execute(
                text("DELETE FROM worker.task_runs WHERE task_id = :id"),
                {"id": str(key)},
            )
            cleanup.execute(text("DELETE FROM worker.tasks WHERE id = :id"), {"id": str(key)})
            cleanup.commit()
        finally:
            cleanup.close()


def _runner():
    sessions = lambda: session_factory.session_for(session_factory.admin_engine())  # noqa: E731
    return Runner(sessions, SystemClock(), graph=_ParkGraph())


def _task_status(task_id):
    session = session_factory.session_for(session_factory.admin_engine())
    try:
        return session.execute(
            text("SELECT status FROM worker.tasks WHERE id = :id"), {"id": str(task_id)}
        ).scalar()
    finally:
        session.close()


def test_park_approve_resume_across_restart(task_id):
    """Waiting survives a restart; resume consumes into a valid token."""
    first = _runner().run_task(str(task_id))
    assert first["approval_status"] == "pending"
    assert _task_status(task_id) == "waiting_for_approval"

    session = session_factory.session_for(session_factory.admin_engine())
    try:
        approvals = ApprovalService(session).list_pending()
        match = [a for a in approvals if a.task_id == task_id]
        assert len(match) == 1
        decided = ApprovalService(session).approve(match[0].id, ApprovalDecide(approver="duty-ops"))
        assert decided.status == "approved"
    finally:
        session.close()
    assert _task_status(task_id) == "running"

    second = _runner().run_task(str(task_id))
    assert second["approval_status"] == "approved"
    params = second["last_action"]["params"]
    verify_submit_token(params["token"], SECRET, str(task_id), dict(params))

    session = session_factory.session_for(session_factory.admin_engine())
    try:
        attempts = session.execute(
            text("SELECT COUNT(*) FROM worker.task_runs WHERE task_id = :id"),
            {"id": str(task_id)},
        ).scalar()
        assert attempts == 2
    finally:
        session.close()

    session = session_factory.session_for(session_factory.admin_engine())
    try:
        status = session.execute(
            text("SELECT status FROM worker.approvals WHERE task_id = :id"),
            {"id": str(task_id)},
        ).scalar()
        assert status == "consumed"
    finally:
        session.close()
