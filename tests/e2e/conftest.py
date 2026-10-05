"""Live-DB fixtures for end-to-end tests (no servers, no LLM).

`tests/e2e` proves the runtime against the real Postgres: journal-first
execution, observation memory, and runner lifecycle. Full hero-path runs
(servers + browser + Mercury) live in `test_hero_path.py` (marked llm).
"""

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
    """One `ns_runner` session with cleanup of journal rows afterwards."""
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
                    "DELETE FROM worker.memory_items WHERE run_id IN "
                    "(SELECT id FROM worker.task_runs WHERE task_id = ANY(:ids))"
                ),
                {"ids": created_tasks},
            )
            cleanup.execute(
                text(
                    "DELETE FROM worker.action_attempts WHERE action_id IN "
                    "(SELECT id FROM worker.actions WHERE run_id IN "
                    "(SELECT id FROM worker.task_runs WHERE task_id = ANY(:ids)))"
                ),
                {"ids": created_tasks},
            )
            cleanup.execute(
                text(
                    "DELETE FROM worker.actions WHERE run_id IN "
                    "(SELECT id FROM worker.task_runs WHERE task_id = ANY(:ids))"
                ),
                {"ids": created_tasks},
            )
            cleanup.execute(
                text("DELETE FROM worker.policy_decisions WHERE task_id = ANY(:ids)"),
                {"ids": created_tasks},
            )
            cleanup.execute(
                text("DELETE FROM worker.task_checkpoints WHERE run_id IN "
                     "(SELECT id FROM worker.task_runs WHERE task_id = ANY(:ids))"),
                {"ids": created_tasks},
            )
            cleanup.execute(
                text("DELETE FROM worker.task_contracts WHERE task_id = ANY(:ids)"),
                {"ids": created_tasks},
            )
            cleanup.execute(
                text("DELETE FROM worker.audit_events WHERE task_id = ANY(:ids)"),
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
