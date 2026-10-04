"""Health endpoint: GET /api/health returns 200 (Phase 1)."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok():
    client = TestClient(create_app())
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "northstar-worker-backend"
    assert "version" in body
