"""Live-DB migration fixture for evidence tests (no servers, no LLM)."""

import pytest
from alembic import command
from alembic.config import Config


@pytest.fixture(scope="session", autouse=True)
def _migrate_head():
    """Migrate to head once per session (tests use throwaway UUID rows)."""
    command.upgrade(Config("database/alembic.ini"), "head")
