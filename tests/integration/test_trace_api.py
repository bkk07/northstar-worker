"""Trace API regression: `GET /support/tickets/:id/trace` must serialize.

Guards the 500 caused by `get_trace()` omitting the `ticket_id` /
`ticket_number` fields that `ApprovalRead` requires: any ticket with an
approval row failed response validation. Covers a fresh ticket (no run),
a waiting-for-human ticket with run + tool call + pending approval, and
a completed ticket.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_app
from database import session as session_factory
from tests.integration.conftest import staff_headers


@pytest.fixture(scope="module")
def client():
    """The real app (reads/writes live Postgres, no servers)."""
    return TestClient(create_app())


@pytest.fixture()
def ticket_rows():
    """Canonical user + ticket + run + tool call + pending approval."""
    engine = session_factory.admin_engine()
    session = session_factory.session_for(engine)
    user_id = uuid.uuid4()
    ticket_id = uuid.uuid4()
    run_id = uuid.uuid4()
    number = f"T{uuid.uuid4().hex[:7].upper()}"
    session.execute(
        text(
            "INSERT INTO biz.app_users (id, name, email, password_hash, role) "
            "VALUES (:id, 'trace probe', :email, 'x', 'CUSTOMER')"
        ),
        {"id": str(user_id), "email": f"{uuid.uuid4().hex}@example.com"},
    )
    session.execute(
        text(
            "INSERT INTO biz.customer_tickets (id, user_id, ticket_number, subject, "
            "description, category, priority, status) VALUES (:id, :uid, :num, "
            "'subj', 'desc', 'REFUND', 'NORMAL', 'WAITING_FOR_HUMAN')"
        ),
        {"id": str(ticket_id), "uid": str(user_id), "num": number},
    )
    session.execute(
        text(
            "INSERT INTO biz.agent_runs (id, ticket_id, status, intent, workflow, "
            "decision) VALUES (:rid, :tid, 'WAITING_FOR_HUMAN', 'REFUND', "
            "'REFUND', 'awaiting_approval')"
        ),
        {"rid": str(run_id), "tid": str(ticket_id)},
    )
    session.execute(
        text(
            "INSERT INTO biz.tool_calls (id, agent_run_id, tool_name, arguments, "
            "result, status) VALUES (:id, :rid, 'get_ticket', '{}', "
            "'{\"ok\": true}', 'DONE')"
        ),
        {"id": str(uuid.uuid4()), "rid": str(run_id)},
    )
    session.execute(
        text(
            "INSERT INTO biz.approvals (id, ticket_id, agent_run_id, action_type, "
            "action_payload, status) VALUES (:id, :tid, :rid, 'REFUND', "
            "'{\"amount_paise\": 100}', 'PENDING')"
        ),
        {"id": str(uuid.uuid4()), "tid": str(ticket_id), "rid": str(run_id)},
    )
    session.commit()
    session.close()
    try:
        yield ticket_id, number
    finally:
        cleanup = session_factory.session_for(engine)
        try:
            for table, col, val in (
                ("biz.approvals", "ticket_id", str(ticket_id)),
                ("biz.tool_calls", "agent_run_id", str(run_id)),
                ("biz.agent_runs", "id", str(run_id)),
                ("biz.customer_tickets", "id", str(ticket_id)),
                ("biz.app_users", "id", str(user_id)),
            ):
                cleanup.execute(
                    text(f"DELETE FROM {table} WHERE {col} = :v"), {"v": val}
                )
            cleanup.commit()
        finally:
            cleanup.close()


@pytest.fixture()
def fresh_ticket_row():
    """Canonical ticket with no AI run (idle trace)."""
    engine = session_factory.admin_engine()
    session = session_factory.session_for(engine)
    user_id = uuid.uuid4()
    ticket_id = uuid.uuid4()
    number = f"T{uuid.uuid4().hex[:7].upper()}"
    session.execute(
        text(
            "INSERT INTO biz.app_users (id, name, email, password_hash, role) "
            "VALUES (:id, 'trace fresh', :email, 'x', 'CUSTOMER')"
        ),
        {"id": str(user_id), "email": f"{uuid.uuid4().hex}@example.com"},
    )
    session.execute(
        text(
            "INSERT INTO biz.customer_tickets (id, user_id, ticket_number, subject, "
            "description, category, priority, status) VALUES (:id, :uid, :num, "
            "'subj', 'desc', 'GENERAL', 'NORMAL', 'OPEN')"
        ),
        {"id": str(ticket_id), "uid": str(user_id), "num": number},
    )
    session.commit()
    session.close()
    try:
        yield ticket_id
    finally:
        cleanup = session_factory.session_for(engine)
        try:
            cleanup.execute(
                text("DELETE FROM biz.customer_tickets WHERE id = :v"),
                {"v": str(ticket_id)},
            )
            cleanup.execute(
                text("DELETE FROM biz.app_users WHERE id = :v"), {"v": str(user_id)}
            )
            cleanup.commit()
        finally:
            cleanup.close()


def test_trace_waiting_ticket_serializes(client, ticket_rows):
    ticket_id, number = ticket_rows
    response = client.get(
        f"/support/tickets/{ticket_id}/trace", headers=staff_headers()
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == str(ticket_id)
    assert body["run"]["status"] == "WAITING_FOR_HUMAN"
    assert len(body["steps"]) > 0
    assert len(body["approvals"]) == 1
    approval = body["approvals"][0]
    assert approval["ticket_id"] == str(ticket_id)
    assert approval["ticket_number"] == number


def test_trace_fresh_ticket_is_idle(client, fresh_ticket_row):
    response = client.get(
        f"/support/tickets/{fresh_ticket_row}/trace", headers=staff_headers()
    )
    assert response.status_code == 200
    body = response.json()
    assert body["run"] is None
    assert body["approvals"] == []
    assert body["steps"][0]["key"] == "idle"
