"""Live-DB fixtures for verifier tests (no servers, no LLM)."""

import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from database import session as session_factory


@pytest.fixture(scope="session", autouse=True)
def _migrate_head():
    """Migrate to head once per session (tests use throwaway UUID rows)."""
    command.upgrade(Config("database/alembic.ini"), "head")


@pytest.fixture()
def runner_session(_migrate_head):
    """One `ns_runner` session with cleanup of verifier rows afterwards."""
    engine = session_factory.runner_engine()
    session = session_factory.session_for(engine)
    created_tasks: list[uuid.UUID] = []
    try:
        yield session, created_tasks
    finally:
        session.close()
        cleanup = session_factory.session_for(session_factory.admin_engine())
        try:
            cleanup.execute(
                text(
                    "DELETE FROM worker.verification_results WHERE run_id IN "
                    "(SELECT id FROM worker.task_runs WHERE task_id = ANY(:ids))"
                ),
                {"ids": created_tasks},
            )
            cleanup.execute(
                text(
                    "DELETE FROM worker.snapshots WHERE run_id IN "
                    "(SELECT id FROM worker.task_runs WHERE task_id = ANY(:ids))"
                ),
                {"ids": created_tasks},
            )
            cleanup.execute(
                text("DELETE FROM worker.task_runs WHERE task_id = ANY(:ids)"),
                {"ids": created_tasks},
            )
            cleanup.execute(
                text("DELETE FROM worker.tasks WHERE id = ANY(:ids)"),
                {"ids": created_tasks},
            )
            cleanup.commit()
        finally:
            cleanup.close()
