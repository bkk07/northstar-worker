"""Evaluation API: recorded runs and the scenario catalog (Phase 27)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.integration.conftest import staff_headers


@pytest.fixture(scope="module")
def client():
    """The real app (reads live Postgres, no servers)."""
    return TestClient(create_app())


def _payload(suite="seeded-smoke"):
    return {
        "suite": suite,
        "scenario_count": 2,
        "metrics": {"scenarios": 2, "task_success_rate": 1.0, "unsafe_action_rate": 0.0},
        "results": [
            {
                "scenario_id": "S5",
                "expected_outcome": "BLOCK",
                "actual_outcome": "BLOCK",
                "outcome_ok": True,
                "scores": {"unsafe": False},
            },
            {
                "scenario_id": "S4",
                "expected_outcome": "CLARIFY",
                "actual_outcome": "CLARIFY",
                "outcome_ok": True,
                "scores": {"unsafe": False},
            },
        ],
        "report_md": "# smoke",
    }


def test_record_list_get_run(client):
    """Recorded runs persist with their per-scenario drilldown."""
    created = client.post("/api/eval/runs", headers=staff_headers(), json=_payload()).json()
    assert created["suite"] == "seeded-smoke"
    assert created["metrics"]["task_success_rate"] == 1.0
    assert uuid.UUID(created["id"])

    listed = client.get("/api/eval/runs", headers=staff_headers()).json()
    assert any(run["id"] == created["id"] for run in listed)

    detail = client.get(f"/api/eval/runs/{created['id']}", headers=staff_headers()).json()
    assert detail["run"]["id"] == created["id"]
    assert [r["scenario_id"] for r in detail["results"]] == ["S4", "S5"]
    assert all(r["outcome_ok"] for r in detail["results"])
    assert detail["run"]["report_md"] == "# smoke"


def test_unknown_run_404s(client):
    """Unknown runs 404."""
    assert client.get(f"/api/eval/runs/{uuid.uuid4()}", headers=staff_headers()).status_code == 404


def test_scenarios_serve_the_catalog(client):
    """The catalog endpoint mirrors the oracle's source file."""
    body = client.get("/api/eval/scenarios", headers=staff_headers()).json()
    assert len(body) == 40
    by_id = {row["id"]: row for row in body}
    assert by_id["S5"]["expected_outcome"] == "BLOCK"
    assert by_id["S1"]["ticket_code"] == "TCK-101"
    assert all(row["task"] and row["expected_effects"] is not None for row in body)


def test_scenarios_serve_the_held_out_suite(client):
    """The sealed held-out catalog is served with its own suite flag."""
    body = client.get("/api/eval/scenarios", headers=staff_headers(), params={"suite": "held_out"}).json()
    assert len(body) == 15
    by_id = {row["id"]: row for row in body}
    assert by_id["S907"]["expected_outcome"] == "CLARIFY"
    assert by_id["S915"]["expected_outcome"] == "INCONCLUSIVE"
    assert all(row["id"].startswith("S9") for row in body)


def test_oracle_resolves_held_out_ids(client):
    """The control oracle derives held-out expectations too."""
    response = client.get(
        "/api/control/oracle/S911", headers={"Authorization": "Bearer local-operator-token"}
    )
    assert response.status_code == 200
    assert response.json()["expected_outcome"] == "BLOCK"
