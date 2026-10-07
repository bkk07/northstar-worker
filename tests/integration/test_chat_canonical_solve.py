"""Chat quarantine (#6): `TKT-` solves run the canonical ticket path, never a worker task."""

import threading
import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import create_app
from tests.integration.conftest import staff_headers


class _SyncThread(threading.Thread):
    """Background chat launches run inline (deterministic); every other
    thread (e.g. the TestClient portal) keeps real threading behavior.

    A plain fake `Thread` without `join` deadlocks the TestClient portal,
    hanging the whole file — hence the subclass.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        name = kwargs.get("name")
        if name is None and len(args) >= 3:
            name = args[2]
        self._inline = (name or "").startswith("chat-canonical-")

    def start(self):
        if self._inline:
            self.run()
        else:
            super().start()


def _patch(monkeypatch, *, ticket_row, active_run=None, solve=None):
    """Stub canonical lookup + run state; forbid worker-task creation."""
    import app.services.worker.chat_service as chat_service
    from app.repositories.agent.agent_repository import AgentRepository
    from app.services.agent_run import agent_run_service
    from app.services.worker.task_service import TaskService

    monkeypatch.setattr(
        chat_service.CustomerTicketRepository, "get_by_number",
        lambda self, code: ticket_row,
    )
    monkeypatch.setattr(
        AgentRepository, "active_for_ticket", lambda self, tid: active_run
    )
    if solve is not None:
        monkeypatch.setattr(agent_run_service, "solve", solve)
    monkeypatch.setattr(threading, "Thread", _SyncThread)

    def _no_task(self, *args, **kwargs):
        raise AssertionError("worker task must not be created for TKT- solves")

    monkeypatch.setattr(TaskService, "create_task", _no_task)


def test_unknown_tkt_refuses_without_task(monkeypatch):
    _patch(monkeypatch, ticket_row=None)
    client = TestClient(create_app())
    response = client.post(
        "/api/chat", headers=staff_headers(), json={"message": "solve ticket TKT-NOPE01"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "TKT-NOPE01" in body["reply"]
    assert body["task_id"] is None


def test_canonical_tkt_launches_ticket_run_not_worker_task(monkeypatch):
    calls: dict = {}
    tid = uuid.uuid4()

    def _solve(session, *, ticket_id, llm=None):
        calls["ticket_id"] = ticket_id
        return {"run_id": "r1", "status": "RUNNING"}

    _patch(
        monkeypatch,
        ticket_row=SimpleNamespace(id=tid, status="OPEN", resolution=None),
        solve=_solve,
    )
    client = TestClient(create_app())
    response = client.post(
        "/api/chat", headers=staff_headers(), json={"message": "solve ticket TKT-C086C2"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "TKT-C086C2" in body["reply"]
    assert calls.get("ticket_id") == str(tid)
    assert body["task_id"] is None
    hrefs = [a.get("href", "") for a in body["actions"]]
    assert any(h == f"/tickets/{tid}" for h in hrefs)


def test_resolved_tkt_refuses_without_running(monkeypatch):
    tid = uuid.uuid4()
    _patch(
        monkeypatch,
        ticket_row=SimpleNamespace(id=tid, status="RESOLVED", resolution="fixed"),
    )
    client = TestClient(create_app())
    response = client.post(
        "/api/chat", headers=staff_headers(), json={"message": "solve ticket TKT-C086C2"}
    )
    assert response.status_code == 200
    assert "already resolved" in response.json()["reply"].lower()


def test_active_run_refuses_second_launch(monkeypatch):
    tid = uuid.uuid4()
    _patch(
        monkeypatch,
        ticket_row=SimpleNamespace(id=tid, status="OPEN", resolution=None),
        active_run=SimpleNamespace(id=uuid.uuid4()),
    )
    client = TestClient(create_app())
    response = client.post(
        "/api/chat", headers=staff_headers(), json={"message": "solve ticket TKT-C086C2"}
    )
    assert response.status_code == 200
    assert "already has an AI run" in response.json()["reply"]
