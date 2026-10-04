"""Phase 4: role grants — writers, readers, and append-only audit (live DB)."""

import uuid

import pytest
from conftest import make_chain, unique_code
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


def test_app_can_write_biz(app_conn):
    """Sanity: `ns_app` owns business writes."""
    customer_id = uuid.uuid4()
    app_conn.execute(
        text(
            "INSERT INTO biz.customers (id, code, name, email) "
            "VALUES (:id, :code, 'App Writer', :email)"
        ),
        {
            "id": customer_id,
            "code": unique_code("C"),
            "email": f"{uuid.uuid4().hex}@example.com",
        },
    )
    app_conn.commit()


def test_runner_cannot_insert_biz_replacements(admin_conn, runner_conn):
    """`ns_runner` has no write path to business tables."""
    ids = make_chain(admin_conn, "runner-deny")
    with pytest.raises(DBAPIError, match="permission denied"):
        runner_conn.execute(
            text(
                "INSERT INTO biz.replacements (id, order_id, order_item_id, customer_id, "
                "ticket_id, status, mutation_key) VALUES (:id, :oid, :iid, :cid, :tid, "
                "'pending', :key)"
            ),
            {
                "id": uuid.uuid4(),
                "oid": ids["order_id"],
                "iid": ids["item_id"],
                "cid": ids["customer_id"],
                "tid": ids["ticket_id"],
                "key": unique_code("K"),
            },
        )
        runner_conn.commit()
    runner_conn.rollback()


def test_runner_reads_biz_only_via_views(runner_conn):
    """`ns_runner` SELECTs the `worker.v_*` views, never base tables."""
    assert runner_conn.execute(text("SELECT count(*) FROM worker.v_orders")).scalar() >= 0
    assert runner_conn.execute(text("SELECT count(*) FROM worker.v_tickets")).scalar() >= 0
    with pytest.raises(DBAPIError, match="permission denied"):
        runner_conn.execute(text("SELECT count(*) FROM biz.orders"))
    runner_conn.rollback()


def test_verifier_is_read_only(verifier_conn):
    """`ns_verifier` SELECTs everything but writes nothing."""
    assert verifier_conn.execute(text("SELECT count(*) FROM worker.tasks")).scalar() >= 0
    assert verifier_conn.execute(text("SELECT count(*) FROM biz.orders")).scalar() >= 0
    with pytest.raises(DBAPIError, match="permission denied"):
        verifier_conn.execute(
            text(
                "INSERT INTO worker.tasks (id, text, mode, status, current_state, "
                "created_by) VALUES (:id, 'x', 'explicit', 'pending', 'pending', 't')"
            ),
            {"id": uuid.uuid4()},
        )
    verifier_conn.rollback()


def test_audit_is_append_only(app_conn):
    """UPDATE/DELETE on `audit_events` are denied; INSERT works."""
    task_id = uuid.uuid4()
    app_conn.execute(
        text(
            "INSERT INTO worker.tasks (id, text, mode, status, current_state, "
            "created_by) VALUES (:id, 'audit probe', 'explicit', 'pending', 'pending', 't')"
        ),
        {"id": task_id},
    )
    audit_id = uuid.uuid4()
    app_conn.execute(
        text(
            "INSERT INTO worker.audit_events (id, task_id, ts, kind) "
            "VALUES (:id, :tid, now(), 'probe')"
        ),
        {"id": audit_id, "tid": task_id},
    )
    app_conn.commit()
    with pytest.raises(DBAPIError, match="permission denied"):
        app_conn.execute(
            text("UPDATE worker.audit_events SET kind = 'rewritten' WHERE id = :id"),
            {"id": audit_id},
        )
        app_conn.commit()
    app_conn.rollback()
    with pytest.raises(DBAPIError, match="permission denied"):
        app_conn.execute(text("DELETE FROM worker.audit_events WHERE id = :id"), {"id": audit_id})
        app_conn.commit()
    app_conn.rollback()
