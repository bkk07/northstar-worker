"""Live-Postgres fixtures (Phase 4).

Requires the compose DB (`docker compose up -d`, host port 5433).
Engines use NullPool; each test commits or rolls back explicitly.
"""

import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from database import session as session_factory


@pytest.fixture(scope="session", autouse=True)
def _migrate_head():
    """Migrate to head once per session (tests use unique codes)."""
    command.upgrade(Config("database/alembic.ini"), "head")


def _connect(role: str) -> Connection:
    engine: Engine = session_factory.create_role_engine(role)
    return engine.connect()


@pytest.fixture()
def admin_conn(_migrate_head):
    """Superuser connection (setup only, never business writes)."""
    conn = _connect("admin")
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def app_conn(_migrate_head):
    """`ns_app` connection (backend role)."""
    conn = _connect("ns_app")
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def runner_conn(_migrate_head):
    """`ns_runner` connection (agent role)."""
    conn = _connect("ns_runner")
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def verifier_conn(_migrate_head):
    """`ns_verifier` connection (read-only role)."""
    conn = _connect("ns_verifier")
    try:
        yield conn
    finally:
        conn.close()


def unique_code(prefix: str) -> str:
    """Unique human code (fits String(16) columns)."""
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def staff_headers(*, user_id: str | None = None, email: str = "admin@northstar.shop") -> dict:
    """SUPPORT_AGENT JWT headers (signature-checked; no DB row needed).

    Use in integration tests after the security hardening: worker, read,
    shop, ops-login, eval, and direct-commit surfaces require auth.
    """
    import sys

    sys.path.insert(0, "backend")
    from app.core.auth import create_access_token

    token = create_access_token(
        user_id=user_id or str(uuid.uuid4()), email=email, role="SUPPORT_AGENT"
    )
    return {"Authorization": f"Bearer {token}"}


def make_chain(conn: Connection, tag: str, total_paise: int = 500000) -> dict:
    """Insert customer -> order -> item -> ticket; return their ids."""
    customer_id, order_id, item_id, ticket_id = (uuid.uuid4() for _ in range(4))
    conn.execute(
        text(
            "INSERT INTO biz.customers (id, code, name, email) VALUES (:id, :code, :name, :email)"
        ),
        {
            "id": customer_id,
            "code": unique_code("C"),
            "name": f"Test User {tag}",
            "email": f"{uuid.uuid4().hex}@example.com",
        },
    )
    conn.execute(
        text(
            "INSERT INTO biz.orders (id, code, customer_id, status, total_paise, "
            "paid_paise, placed_at) VALUES (:id, :code, :cid, 'delivered', "
            ":total, :total, now())"
        ),
        {"id": order_id, "code": unique_code("O"), "cid": customer_id, "total": total_paise},
    )
    conn.execute(
        text(
            "INSERT INTO biz.order_items (id, order_id, sku, title, qty, unit_paise, "
            "category) VALUES (:id, :oid, 'SKU-1', 'Laptop', 1, :total, 'electronics')"
        ),
        {"id": item_id, "oid": order_id, "total": total_paise},
    )
    conn.execute(
        text(
            "INSERT INTO biz.tickets (id, code, customer_id, order_id, subject, body, "
            "category, status, version) VALUES (:id, :code, :cid, :oid, 'subj', "
            "'body', 'damage', 'open', 1)"
        ),
        {"id": ticket_id, "code": unique_code("T"), "cid": customer_id, "oid": order_id},
    )
    conn.commit()
    return {
        "customer_id": customer_id,
        "order_id": order_id,
        "item_id": item_id,
        "ticket_id": ticket_id,
    }
