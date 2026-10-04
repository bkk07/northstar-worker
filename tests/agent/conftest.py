"""Agent fixtures: migrate to head once per session (Phase 13).

Repository tests write real rows; the migration autouse keeps the local
schema current the same way `tests/integration/conftest.py` does.
"""

import pytest
from alembic import command
from alembic.config import Config


@pytest.fixture(scope="session", autouse=True)
def _migrate_head():
    """Migrate to head once per session (tests use unique rows)."""
    command.upgrade(Config("database/alembic.ini"), "head")
