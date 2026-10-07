"""Worker memory endpoint: sourced items per task (Phase 23)."""

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
def memory_rows():
    """Throwaway task + run + memory rows, cleaned up after."""
    engine = session_factory.admin_engine()
    session = session_factory.session_for(engine)
    task_id, run_id = uuid.uuid4(), uuid.uuid4()
    session.execute(
        text(
            "INSERT INTO worker.tasks (id, text, mode, status, current_state, created_by) "
            "VALUES (:id, 'memory probe', 'explicit', 'running', 'running', 'phase23-test')"
        ),
        {"id": str(task_id)},
    )
    session.execute(
        text("INSERT INTO worker.task_runs (id, task_id, attempt) VALUES (:id, :task, 1)"),
        {"id": str(run_id), "task": str(task_id)},
    )
    session.execute(
        text(
            "INSERT INTO worker.memory_items "
            "(id, run_id, key, value, source_type, source_ref, trust) "
            "VALUES (:id, :run, 'get_order:0:success', '{\"order\": \"o\"}', "
            "'database', 'k', 'trusted')"
        ),
        {"id": str(uuid.uuid4()), "run": str(run_id)},
    )
    session.execute(
        text(
            "INSERT INTO worker.memory_items "
            "(id, run_id, key, value, source_type, source_ref, trust) "
            "VALUES (:id, :run, 'injection:flag:browser_observe:0', "
            "'{\"flags\": [\"system_override\"]}', 'browser', 'k', 'untrusted')"
        ),
        {"id": str(uuid.uuid4()), "run": str(run_id)},
    )
    session.commit()
    session.close()
    try:
        yield task_id
    finally:
        cleanup = session_factory.session_for(engine)
        try:
            cleanup.execute(
                text("DELETE FROM worker.memory_items WHERE run_id = :id"),
                {"id": str(run_id)},
            )
            cleanup.execute(
                text("DELETE FROM worker.task_runs WHERE id = :id"), {"id": str(run_id)}
            )
            cleanup.execute(text("DELETE FROM worker.tasks WHERE id = :id"), {"id": str(task_id)})
            cleanup.commit()
        finally:
            cleanup.close()


def test_memory_lists_provenance_newest_first(client, memory_rows):
    """Each fact shows source, trust, timestamp, and run."""
    body = client.get(f"/api/tasks/{memory_rows}/memory", headers=staff_headers()).json()
    assert len(body) == 2
    by_key = {item["key"]: item for item in body}
    assert by_key["get_order:0:success"]["trust"] == "trusted"
    assert by_key["get_order:0:success"]["source_type"] == "database"
    assert by_key["injection:flag:browser_observe:0"]["trust"] == "untrusted"
    for item in body:
        assert item["run_id"] and item["created_at"]


def test_memory_404_for_unknown_task(client):
    """Unknown tasks 404."""
    assert client.get(f"/api/tasks/{uuid.uuid4()}/memory", headers=staff_headers()).status_code == 404
