"""Phase 4: constraints, triggers, and transition enforcement (live DB)."""

import uuid

import pytest
from conftest import make_chain, unique_code
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from agent.runtime.transitions import ALLOWED_TRANSITIONS


def _insert_replacement(conn, ids, status, key):
    conn.execute(
        text(
            "INSERT INTO biz.replacements (id, order_id, order_item_id, customer_id, "
            "ticket_id, status, mutation_key) VALUES (:id, :oid, :iid, :cid, :tid, "
            ":status, :key)"
        ),
        {
            "id": uuid.uuid4(),
            "oid": ids["order_id"],
            "iid": ids["item_id"],
            "cid": ids["customer_id"],
            "tid": ids["ticket_id"],
            "status": status,
            "key": key,
        },
    )


def test_duplicate_active_replacement_rejected(admin_conn):
    """Second active replacement for one item collides instead of duplicating."""
    ids = make_chain(admin_conn, "dup-repl")
    _insert_replacement(admin_conn, ids, "pending", unique_code("K"))
    admin_conn.commit()
    with pytest.raises(DBAPIError, match="uq_replacements_item_active"):
        _insert_replacement(admin_conn, ids, "pending", unique_code("K"))
        admin_conn.commit()
    admin_conn.rollback()


def test_cancelled_replacement_frees_the_item(admin_conn):
    """Partial index: only pending/shipped rows block a new replacement."""
    ids = make_chain(admin_conn, "cancel-repl")
    _insert_replacement(admin_conn, ids, "cancelled", unique_code("K"))
    admin_conn.commit()
    _insert_replacement(admin_conn, ids, "pending", unique_code("K"))
    admin_conn.commit()


def test_refund_exceeding_paid_rejected(admin_conn):
    """Last-defense trigger: refunds on an order never exceed paid."""
    ids = make_chain(admin_conn, "refund-guard", total_paise=500000)
    with pytest.raises(DBAPIError, match="exceeds paid"):
        admin_conn.execute(
            text(
                "INSERT INTO biz.refunds (id, order_id, customer_id, ticket_id, "
                "amount_paise, status, mutation_key) VALUES (:id, :oid, :cid, :tid, "
                "600000, 'pending', :key)"
            ),
            {
                "id": uuid.uuid4(),
                "oid": ids["order_id"],
                "cid": ids["customer_id"],
                "tid": ids["ticket_id"],
                "key": unique_code("K"),
            },
        )
        admin_conn.commit()
    admin_conn.rollback()
    admin_conn.execute(
        text(
            "INSERT INTO biz.refunds (id, order_id, customer_id, ticket_id, "
            "amount_paise, status, mutation_key) VALUES (:id, :oid, :cid, :tid, "
            "250000, 'pending', :key)"
        ),
        {
            "id": uuid.uuid4(),
            "oid": ids["order_id"],
            "cid": ids["customer_id"],
            "tid": ids["ticket_id"],
            "key": unique_code("K"),
        },
    )
    admin_conn.commit()


def test_zero_refund_rejected(admin_conn):
    """CHECK amount_paise > 0."""
    ids = make_chain(admin_conn, "refund-zero")
    with pytest.raises(DBAPIError, match="amount_positive"):
        admin_conn.execute(
            text(
                "INSERT INTO biz.refunds (id, order_id, customer_id, ticket_id, "
                "amount_paise, status, mutation_key) VALUES (:id, :oid, :cid, :tid, "
                "0, 'pending', :key)"
            ),
            {
                "id": uuid.uuid4(),
                "oid": ids["order_id"],
                "cid": ids["customer_id"],
                "tid": ids["ticket_id"],
                "key": unique_code("K"),
            },
        )
        admin_conn.commit()
    admin_conn.rollback()


def test_order_paid_lte_total_check(admin_conn):
    """CHECK paid_paise <= total_paise on orders."""
    customer_id = uuid.uuid4()
    admin_conn.execute(
        text(
            "INSERT INTO biz.customers (id, code, name, email) "
            "VALUES (:id, :code, 'Check User', :email)"
        ),
        {"id": customer_id, "code": unique_code("C"), "email": f"{uuid.uuid4().hex}@x.com"},
    )
    with pytest.raises(DBAPIError, match="paid_lte_total"):
        admin_conn.execute(
            text(
                "INSERT INTO biz.orders (id, code, customer_id, status, total_paise, "
                "paid_paise, placed_at) VALUES (:id, :code, :cid, 'placed', 100, "
                "200, now())"
            ),
            {"id": uuid.uuid4(), "code": unique_code("O"), "cid": customer_id},
        )
        admin_conn.commit()
    admin_conn.rollback()


def _insert_task(conn, status):
    task_id = uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO worker.tasks (id, text, mode, status, current_state, "
            "created_by) VALUES (:id, 'do thing', 'explicit', :status, :status, 'test')"
        ),
        {"id": task_id, "status": status},
    )
    conn.commit()
    return task_id


def test_illegal_task_transition_rejected_by_db(admin_conn):
    """The DB trigger rejects pending -> succeeded; the legal path works."""
    task_id = _insert_task(admin_conn, "pending")
    with pytest.raises(DBAPIError, match="illegal task transition"):
        admin_conn.execute(
            text("UPDATE worker.tasks SET status = 'succeeded' WHERE id = :id"),
            {"id": task_id},
        )
        admin_conn.commit()
    admin_conn.rollback()
    admin_conn.execute(
        text("UPDATE worker.tasks SET status = 'running' WHERE id = :id"), {"id": task_id}
    )
    admin_conn.commit()
    admin_conn.execute(
        text("UPDATE worker.tasks SET status = 'succeeded' WHERE id = :id"), {"id": task_id}
    )
    admin_conn.commit()


def test_transition_table_matches_code(admin_conn):
    """Seeded rows equal agent.runtime.transitions.ALLOWED_TRANSITIONS."""
    rows = admin_conn.execute(
        text("SELECT from_status, to_status FROM worker.allowed_transitions")
    ).all()
    expected = {(frm.value, to.value) for frm, tos in ALLOWED_TRANSITIONS.items() for to in tos}
    assert set(rows) == expected


def test_trigram_index_and_runner_views_exist(admin_conn):
    """Look-alike index and the runner's read views are present."""
    index = admin_conn.execute(
        text(
            "SELECT indexname FROM pg_indexes "
            "WHERE schemaname = 'biz' AND indexname = 'ix_customers_name_trgm'"
        )
    ).scalar()
    assert index == "ix_customers_name_trgm"
    views = {
        row[0]
        for row in admin_conn.execute(
            text(
                "SELECT viewname FROM pg_views WHERE schemaname = 'worker' AND viewname LIKE 'v_%'"
            )
        ).all()
    }
    assert {"v_customers", "v_orders", "v_tickets"} <= views
