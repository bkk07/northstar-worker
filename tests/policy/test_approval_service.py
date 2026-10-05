"""Agent approval service: park, consume, and binding enforcement (Phase 22).

Live Postgres with throwaway task/run rows. The S3 arc runs through the
real node path: park on HUMAN_APPROVAL, approve, resume with a token the
MCP guard accepts. Replays, expired rows, and changed params never yield
a token.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from agent.ports.clock import SystemClock
from agent.services.approval_service import ApprovalService
from database import session as session_factory
from database.models.worker.flow import Approval
from database.models.worker.task import Task, TaskRun
from mcp_server.token_guard import verify_submit_token

SECRET = "test-secret"


def _action(amount=3500000):
    return {
        "tool": "browser_submit",
        "params": {
            "effect": "refund.create",
            "ref": "e9",
            "order_id": "o-1944",
            "ticket_id": "t-103",
            "amount_paise": amount,
        },
        "rationale": "test",
    }


def _decision():
    return {"outcome": "human_approval", "rule_id": "P-REF-003", "reason": "needs approval"}


@pytest.fixture()
def run_ids():
    """Throwaway task + run rows, cleaned up with their approvals."""
    engine = session_factory.admin_engine()
    session = session_factory.session_for(engine)
    task = Task(
        id=uuid.uuid4(),
        text="refund Rs. 35,000",
        mode="explicit",
        status="running",
        current_state="running",
        created_by="phase22-test",
    )
    run = TaskRun(id=uuid.uuid4(), task_id=task.id, attempt=1)
    session.add_all([task, run])
    session.commit()
    keys = (task.id, run.id)
    session.close()
    try:
        yield keys
    finally:
        cleanup = session_factory.session_for(engine)
        try:
            cleanup.query(Approval).filter(Approval.task_id == task.id).delete(
                synchronize_session=False
            )
            cleanup.query(TaskRun).filter(TaskRun.id == run.id).delete(synchronize_session=False)
            cleanup.query(Task).filter(Task.id == task.id).delete(synchronize_session=False)
            cleanup.commit()
        finally:
            cleanup.close()


def _service():
    sessions = lambda: session_factory.session_for(session_factory.admin_engine())  # noqa: E731
    return ApprovalService(sessions, SECRET, SystemClock())


def _row(task_id):
    session = session_factory.session_for(session_factory.admin_engine())
    try:
        return (
            session.query(Approval)
            .filter(Approval.task_id == task_id)
            .order_by(Approval.created_at.desc())
            .first()
        )
    finally:
        session.close()


def _set_status(task_id, status):
    session = session_factory.session_for(session_factory.admin_engine())
    try:
        row = (
            session.query(Approval)
            .filter(Approval.task_id == task_id)
            .order_by(Approval.created_at.desc())
            .first()
        )
        row.status = status
        session.commit()
        return row.id
    finally:
        session.close()


def test_park_creates_bound_pending_request(run_ids):
    """First visit parks and binds (task, action, payload hash, 24h)."""
    task_id, run_id = run_ids
    before = datetime.now(UTC)
    outcome = _service().evaluate(str(task_id), str(run_id), _action(), _decision())
    assert outcome["approval_status"] == "pending"
    row = _row(task_id)
    assert row is not None and row.status == "pending"
    assert row.requested_action == "browser_submit"
    assert row.policy_rule_id == "P-REF-003"
    assert row.params_hash and len(row.params_hash) == 64
    assert before + timedelta(hours=23) < row.expires_at <= before + timedelta(hours=25)
    assert "token" not in outcome.get("last_action", {}).get("params", {})


def test_second_visit_reuses_the_open_request(run_ids):
    """No duplicate rows while the request is open."""
    task_id, run_id = run_ids
    service = _service()
    first = service.evaluate(str(task_id), str(run_id), _action(), _decision())
    second = service.evaluate(str(task_id), str(run_id), _action(), _decision())
    assert first["approval_ref"] == second["approval_ref"]


def test_approved_consumes_single_use_token(run_ids):
    """Resume consumes once; the token passes the MCP guard; replay parks."""
    task_id, run_id = run_ids
    service = _service()
    service.evaluate(str(task_id), str(run_id), _action(), _decision())
    _set_status(task_id, "approved")
    action = _action()
    outcome = service.evaluate(str(task_id), str(run_id), action, _decision())
    assert outcome["approval_status"] == "approved"
    token = outcome["last_action"]["params"]["token"]
    verify_submit_token(token, SECRET, str(task_id), dict(action["params"]))
    assert _row(task_id).status == "consumed"
    replay = service.evaluate(str(task_id), str(run_id), action, _decision())
    assert replay["approval_status"] == "pending"
    assert "token" not in replay.get("last_action", {}).get("params", {})


def test_changed_params_invalidate_the_approval(run_ids):
    """An approval for one payload never authorizes another."""
    task_id, run_id = run_ids
    service = _service()
    service.evaluate(str(task_id), str(run_id), _action(), _decision())
    _set_status(task_id, "approved")
    outcome = service.evaluate(str(task_id), str(run_id), _action(amount=3500001), _decision())
    assert outcome["approval_status"] == "pending"
    assert "token" not in outcome.get("last_action", {}).get("params", {})
    assert _row(task_id).status == "pending"


def test_rejected_carries_without_mutation(run_ids):
    """Rejected ends the wait; no token is ever attached."""
    task_id, run_id = run_ids
    service = _service()
    service.evaluate(str(task_id), str(run_id), _action(), _decision())
    _set_status(task_id, "rejected")
    outcome = service.evaluate(str(task_id), str(run_id), _action(), _decision())
    assert outcome["approval_status"] == "rejected"
    assert "token" not in outcome.get("last_action", {}).get("params", {})


def test_expired_carries_and_never_issues(run_ids):
    """Overdue rows flip to expired on read and authorize nothing."""
    task_id, run_id = run_ids
    service = _service()
    service.evaluate(str(task_id), str(run_id), _action(), _decision())
    session = session_factory.session_for(session_factory.admin_engine())
    try:
        row = session.query(Approval).filter(Approval.task_id == task_id).first()
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()
    finally:
        session.close()
    outcome = service.evaluate(str(task_id), str(run_id), _action(), _decision())
    assert outcome["approval_status"] == "expired"
    assert _row(task_id).status == "expired"
