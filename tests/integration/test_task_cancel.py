"""Phase 20: task cancel endpoint (live DB, TestClient, no servers)."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_cancel_pending_task():
    """A pending task cancels cleanly (operator stop switch)."""
    client = TestClient(create_app())
    created = client.post("/api/tasks", json={"text": "cancel me"})
    assert created.status_code == 201
    task_id = created.json()["id"]
    cancelled = client.post(f"/api/tasks/{task_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_cancel_terminal_task_conflicts():
    """Double-cancel answers 409 (terminal states never move)."""
    client = TestClient(create_app())
    task_id = client.post("/api/tasks", json={"text": "cancel twice"}).json()["id"]
    assert client.post(f"/api/tasks/{task_id}/cancel").status_code == 200
    second = client.post(f"/api/tasks/{task_id}/cancel")
    assert second.status_code == 409


def test_cancel_missing_task_404():
    """Unknown ids 404 (no silent no-ops)."""
    client = TestClient(create_app())
    response = client.post("/api/tasks/00000000-0000-0000-0000-000000000000/cancel")
    assert response.status_code == 404
