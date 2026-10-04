"""Phase 4: migrations are reversible (live DB).

Self-contained: downgrades to base, asserts the schema is gone, upgrades
back to head, and asserts the world is whole. Other tests use unique
codes, so the cycle is safe to run in any order.
"""

from alembic import command
from alembic.config import Config
from sqlalchemy import text


def _table_exists(conn, schema, table) -> bool:
    return (
        conn.execute(text("SELECT to_regclass(:name)"), {"name": f"{schema}.{table}"}).scalar()
        is not None
    )


def test_migration_downgrade_upgrade_cycle(admin_conn):
    """base -> head round-trip restores every table and the transition seed."""
    cfg = Config("database/alembic.ini")
    command.downgrade(cfg, "base")
    try:
        assert not _table_exists(admin_conn, "biz", "customers")
        assert not _table_exists(admin_conn, "worker", "tasks")
    finally:
        command.upgrade(cfg, "head")
    assert _table_exists(admin_conn, "biz", "customers")
    assert _table_exists(admin_conn, "worker", "tasks")
    assert _table_exists(admin_conn, "worker", "audit_events")
    seed_count = admin_conn.execute(
        text("SELECT count(*) FROM worker.allowed_transitions")
    ).scalar()
    assert seed_count == 18
