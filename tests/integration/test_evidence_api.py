"""Worker evidence API: tasks, history, packet, shots, proof (Phase 24)."""

import datetime
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_app
from database import session as session_factory
from tests.integration.conftest import staff_headers


@pytest.fixture(scope="module")
def client():
    """The real app (reads live Postgres, no servers)."""
    return TestClient(create_app())


@pytest.fixture()
def task_rows():
    """Throwaway task with history, packet, shots, and proof rows."""
    engine = session_factory.admin_engine()
    session = session_factory.session_for(engine)
    task_id, run_id = uuid.uuid4(), uuid.uuid4()
    now = datetime.datetime.now(datetime.UTC)
    session.execute(
        text(
            "INSERT INTO worker.tasks (id, text, mode, status, current_state, created_by) "
            "VALUES (:id, 'refund Rs. 100,000', 'explicit', 'blocked', 'blocked', 'phase24-test')"
        ),
        {"id": str(task_id)},
    )
    session.execute(
        text("INSERT INTO worker.task_runs (id, task_id, attempt) VALUES (:id, :task, 1)"),
        {"id": str(run_id), "task": str(task_id)},
    )
    session.execute(
        text(
            "INSERT INTO worker.audit_events "
            "(id, task_id, run_id, ts, kind, retry_count, payload) "
            "VALUES (:id, :task, :run, :ts, 'policy.decision', 0, "
            '\'{"rule_id": "P-OWN-001"}\')'
        ),
        {"id": str(uuid.uuid4()), "task": str(task_id), "run": str(run_id), "ts": now},
    )
    session.execute(
        text(
            "INSERT INTO worker.evidence (id, task_id, packet, summary) "
            "VALUES (:id, :task, "
            '\'{"type": "packet/v1", "status": "blocked"}\', \'BLOCKED: x\')'
        ),
        {"id": str(uuid.uuid4()), "task": str(task_id)},
    )
    session.execute(
        text(
            "INSERT INTO worker.evidence (id, task_id, packet, summary) "
            "VALUES (:id, :task, "
            '\'{"type": "screenshot/v1", "run_id": "'
            + str(run_id)
            + '", "label": "after-submit", "path": "shots/after.png"}\', \'shot\')'
        ),
        {"id": str(uuid.uuid4()), "task": str(task_id)},
    )
    session.execute(
        text(
            "INSERT INTO worker.verification_results "
            "(id, run_id, verdict, invariants, diff, computed_at) "
            "VALUES (:id, :run, 'failed', '{}', '{}', :ts)"
        ),
        {"id": str(uuid.uuid4()), "run": str(run_id), "ts": now},
    )
    session.commit()
    session.close()
    try:
        yield task_id, run_id
    finally:
        cleanup = session_factory.session_for(engine)
        try:
            cleanup.execute(
                text("DELETE FROM worker.verification_results WHERE run_id = :id"),
                {"id": str(run_id)},
            )
            cleanup.execute(
                text("DELETE FROM worker.evidence WHERE task_id = :id"), {"id": str(task_id)}
            )
            cleanup.execute(
                text("DELETE FROM worker.audit_events WHERE task_id = :id"),
                {"id": str(task_id)},
            )
            cleanup.execute(
                text("DELETE FROM worker.task_runs WHERE id = :id"), {"id": str(run_id)}
            )
            cleanup.execute(text("DELETE FROM worker.tasks WHERE id = :id"), {"id": str(task_id)})
            cleanup.commit()
        finally:
            cleanup.close()


def test_task_list_contains_task_and_filters_status(client, task_rows):
    """The queue lists newest first with an optional status filter."""
    task_id, _ = task_rows
    body = client.get("/api/tasks?limit=50", headers=staff_headers()).json()
    assert any(item["id"] == str(task_id) for item in body)
    assert client.get("/api/tasks?status=blocked", headers=staff_headers()).json() != []
    assert all(
        item["status"] == "blocked" for item in client.get("/api/tasks?status=blocked", headers=staff_headers()).json()
    )


def test_event_history_replays_oldest_first(client, task_rows):
    """History carries kind, node, and structured payload."""
    task_id, _ = task_rows
    body = client.get(f"/api/tasks/{task_id}/events/history", headers=staff_headers()).json()
    assert len(body) == 1
    assert body[0]["kind"] == "policy.decision"
    assert body[0]["payload"] == {"rule_id": "P-OWN-001"}
    assert "seq" in body[0] and "retry_count" in body[0]


def test_evidence_packet_and_screenshots(client, task_rows):
    """The packet plus the per-run screenshot index."""
    task_id, run_id = task_rows
    packet = client.get(f"/api/tasks/{task_id}/evidence", headers=staff_headers()).json()
    assert packet["packet"]["status"] == "blocked"
    assert packet["summary"].startswith("BLOCKED")
    shots = client.get(f"/api/tasks/{task_id}/evidence/screenshots", headers=staff_headers()).json()
    assert len(shots) == 1
    assert shots[0]["run_id"] == str(run_id)
    assert shots[0]["path"] == "shots/after.png"


def test_verification_lists_persisted_verdicts(client, task_rows):
    """The proof behind the packet, oldest first."""
    task_id, run_id = task_rows
    body = client.get(f"/api/tasks/{task_id}/verification", headers=staff_headers()).json()
    assert len(body) == 1
    assert body[0]["run_id"] == str(run_id)
    assert body[0]["verdict"] == "failed"


def test_unknown_task_404s(client):
    """Unknown tasks 404 on every evidence route."""
    missing = uuid.uuid4()
    assert client.get(f"/api/tasks/{missing}/events/history", headers=staff_headers()).status_code == 404
    assert client.get(f"/api/tasks/{missing}/evidence", headers=staff_headers()).status_code == 404
    assert client.get(f"/api/tasks/{missing}/evidence/screenshots", headers=staff_headers()).status_code == 404
    assert client.get(f"/api/tasks/{missing}/verification", headers=staff_headers()).status_code == 404
