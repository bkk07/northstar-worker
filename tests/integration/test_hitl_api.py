"""HITL worker API: approval and clarification queues (Phase 22).

TestClient against the real app with live Postgres. Proves the operator
flow end to end at the HTTP layer: pending queues list, approve/reject
and answer are single-use and requeue the parked task, and expired or
replayed decisions are rejected.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_app
from database import session as session_factory
from tests.integration.conftest import staff_headers


@pytest.fixture(scope="module")
def client():
    """The real app (reads/writes live Postgres, no servers)."""
    return TestClient(create_app())


@pytest.fixture()
def task_rows():
    """Throwaway tasks + approval + clarification rows, cleaned up after."""
    engine = session_factory.admin_engine()
    session = session_factory.session_for(engine)
    approval_task = uuid.uuid4()
    clarify_task = uuid.uuid4()
    approval_id = uuid.uuid4()
    clarification_id = uuid.uuid4()
    session.execute(
        text(
            "INSERT INTO worker.tasks (id, text, mode, status, current_state, created_by) "
            "VALUES (:id, 'hitl probe', 'explicit', 'waiting_for_approval', "
            "'waiting_for_approval', 'phase22-test')"
        ),
        {"id": str(approval_task)},
    )
    session.execute(
        text(
            "INSERT INTO worker.tasks (id, text, mode, status, current_state, created_by) "
            "VALUES (:id, 'hitl probe', 'explicit', 'waiting_for_clarification', "
            "'waiting_for_clarification', 'phase22-test')"
        ),
        {"id": str(clarify_task)},
    )
    session.execute(
        text(
            "INSERT INTO worker.approvals (id, task_id, requested_action, params, "
            "params_hash, reason, policy_rule_id, status, expires_at) "
            "VALUES (:id, :task, 'browser_submit', '{}', 'h', 'needs approval', "
            "'P-REF-003', 'pending', :exp)"
        ),
        {
            "id": str(approval_id),
            "task": str(approval_task),
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
    )
    session.execute(
        text(
            "INSERT INTO worker.clarifications (id, task_id, kind, question, status) "
            "VALUES (:id, :task, 'operator', 'Which order?', 'pending')"
        ),
        {"id": str(clarification_id), "task": str(clarify_task)},
    )
    session.commit()
    session.close()
    try:
        yield approval_task, approval_id, clarify_task, clarification_id
    finally:
        cleanup = session_factory.session_for(engine)
        try:
            cleanup.execute(
                text("DELETE FROM worker.approvals WHERE id = :id"),
                {"id": str(approval_id)},
            )
            cleanup.execute(
                text("DELETE FROM worker.clarifications WHERE id = :id"),
                {"id": str(clarification_id)},
            )
            for tid in (approval_task, clarify_task):
                cleanup.execute(text("DELETE FROM worker.tasks WHERE id = :id"), {"id": str(tid)})
            cleanup.commit()
        finally:
            cleanup.close()


def _task_status(task_id):
    session = session_factory.session_for(session_factory.admin_engine())
    try:
        return session.execute(
            text("SELECT status FROM worker.tasks WHERE id = :id"), {"id": str(task_id)}
        ).scalar()
    finally:
        session.close()


def test_list_pending_approvals(client, task_rows):
    """The queue shows action, params, reason, and rule."""
    _, approval_id, _, _ = task_rows
    body = client.get("/api/approvals", headers=staff_headers()).json()
    match = [a for a in body if a["id"] == str(approval_id)][0]
    assert match["requested_action"] == "browser_submit"
    assert match["policy_rule_id"] == "P-REF-003"
    assert match["status"] == "pending"


def test_approve_requeues_and_is_single_use(client, task_rows):
    """Approve flips once, requeues the task, and replays 409."""
    task_id, approval_id, _, _ = task_rows
    body = client.post(
        f"/api/approvals/{approval_id}/approve", headers=staff_headers(), json={"approver": "duty-ops"}
    ).json()
    assert body["status"] == "approved" and body["approver"] == "duty-ops"
    assert _task_status(task_id) == "running"
    replay = client.post(f"/api/approvals/{approval_id}/approve", headers=staff_headers(), json={"approver": "duty-ops"})
    assert replay.status_code == 409


def test_reject_requeues_for_blocked_finalize(client, task_rows):
    """Reject flips once and requeues (the graph finalizes BLOCKED)."""
    task_id, approval_id, _, _ = task_rows
    body = client.post(f"/api/approvals/{approval_id}/reject", headers=staff_headers(), json={"approver": "duty-ops"}).json()
    assert body["status"] == "rejected"
    assert _task_status(task_id) == "running"


def test_expired_approvals_are_rejected(client, task_rows):
    """Overdue rows read expired and refuse decisions."""
    _, approval_id, _, _ = task_rows
    session = session_factory.session_for(session_factory.admin_engine())
    try:
        session.execute(
            text("UPDATE worker.approvals SET expires_at = :exp WHERE id = :id"),
            {"exp": datetime.now(UTC) - timedelta(seconds=1), "id": str(approval_id)},
        )
        session.commit()
    finally:
        session.close()
    response = client.post(f"/api/approvals/{approval_id}/approve", headers=staff_headers(), json={"approver": "duty-ops"})
    assert response.status_code == 409
    queued = [a["id"] for a in client.get("/api/approvals", headers=staff_headers()).json()]
    assert str(approval_id) not in queued


def test_approval_404(client):
    """Unknown approvals 404."""
    response = client.post(f"/api/approvals/{uuid.uuid4()}/approve", headers=staff_headers(), json={"approver": "duty-ops"})
    assert response.status_code == 404


def test_answer_clarification_requeues_and_is_single_use(client, task_rows):
    """Answer flips once, requeues the task, and replays 409."""
    _, _, task_id, clarification_id = task_rows
    body = client.post(
        f"/api/clarifications/{clarification_id}/answer",
        headers=staff_headers(),
        json={"answer": "cancel the mug", "answered_by": "duty-ops"},
    ).json()
    assert body["status"] == "answered" and body["answer"] == "cancel the mug"
    assert _task_status(task_id) == "running"
    replay = client.post(
        f"/api/clarifications/{clarification_id}/answer",
        headers=staff_headers(),
        json={"answer": "again", "answered_by": "duty-ops"},
    )
    assert replay.status_code == 409


def test_list_pending_clarifications(client, task_rows):
    """The queue shows kind and question."""
    _, _, _, clarification_id = task_rows
    body = client.get("/api/clarifications", headers=staff_headers()).json()
    match = [c for c in body if c["id"] == str(clarification_id)][0]
    assert match["kind"] == "operator" and match["status"] == "pending"
