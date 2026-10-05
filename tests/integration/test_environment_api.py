"""Worker environment proxy: cookie guard, no token leakage (Phase 26)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_app
from database import session as session_factory


@pytest.fixture(scope="module")
def client():
    """The real app (reads live Postgres, no servers)."""
    return TestClient(create_app())


def _login(client) -> dict:
    """Sandbox login (httponly cookie jar keeps the session)."""
    response = client.post("/api/ops/auth/login", json={"agent_name": "phase26-test"})
    assert response.status_code == 200
    return dict(response.cookies)


def test_environment_requires_login(client):
    """Anonymous browsers get 401 on every environment route."""
    assert client.get("/api/environment/status").status_code == 401
    assert client.post("/api/environment/faults", json={}).status_code == 401
    assert client.post("/api/environment/reset").status_code == 401
    assert client.post("/api/environment/seed").status_code == 401


def test_status_reports_queues(client):
    """Logged-in operators see liveness plus queue depths."""
    cookies = _login(client)
    body = client.get("/api/environment/status", cookies=cookies).json()
    assert body["backend"] == "ok"
    assert body["database"] == "ok"
    assert body["pending_tasks"] >= 0
    assert body["pending_approvals"] >= 0
    assert body["pending_clarifications"] >= 0


def test_arm_fault_through_proxy_without_operator_token(client):
    """The cookie suffices; the operator token never reaches the browser."""
    cookies = _login(client)
    body = client.post(
        "/api/environment/faults",
        cookies=cookies,
        json={
            "fault_type": "TIMEOUT",
            "target": "ops.refunds",
            "trigger": {"nth_call": 1},
            "params": {},
        },
    ).json()
    assert body["fault_type"] == "TIMEOUT"
    assert body["armed"] is True
    engine = session_factory.admin_engine()
    cleanup = session_factory.session_for(engine)
    try:
        cleanup.execute(text("DELETE FROM biz.fault_plans WHERE id = :id"), {"id": str(body["id"])})
        cleanup.commit()
    finally:
        cleanup.close()
    assert uuid.UUID(body["id"])
