"""Chat endpoint: intent routing over live Postgres (run launch stubbed)."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_app
from app.services.worker import chat_runner
from app.services.worker.chat_runner import _mark_cancelled


@pytest.fixture(autouse=True)
def _deterministic_replies(monkeypatch):
    """Pin chat to deterministic drafts (narration needs no model here)."""
    monkeypatch.setenv("CHAT_USE_MODEL", "0")


def _insert_ticket(conn, tag: str) -> dict:
    """Customer -> order -> TCK- ticket chain with a fixed code prefix."""
    customer_id, order_id, ticket_id = (uuid.uuid4() for _ in range(3))
    code = f"TCK-{tag[:6].upper()}{uuid.uuid4().hex[:2].upper()}"
    order_code = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    conn.execute(
        text(
            "INSERT INTO biz.customers (id, code, name, email) VALUES "
            "(:id, :code, :name, :email)"
        ),
        {
            "id": customer_id,
            "code": f"C{uuid.uuid4().hex[:8]}",
            "name": f"Chat User {tag}",
            "email": f"{uuid.uuid4().hex}@example.com",
        },
    )
    conn.execute(
        text(
            "INSERT INTO biz.orders (id, code, customer_id, status, total_paise, "
            "paid_paise, placed_at) VALUES (:id, :code, :cid, 'delivered', "
            "10000, 10000, now())"
        ),
        {"id": order_id, "code": order_code, "cid": customer_id},
    )
    conn.execute(
        text(
            "INSERT INTO biz.tickets (id, code, customer_id, order_id, subject, body, "
            "category, status, version) VALUES (:id, :code, :cid, :oid, "
            "'Screen cracked', 'The screen arrived cracked', 'damage', 'open', 1)"
        ),
        {"id": ticket_id, "code": code, "cid": customer_id, "oid": order_id},
    )
    conn.commit()
    return {"code": code, "order_code": order_code}


def test_chat_help_answers_capabilities():
    """Small talk answers with the capability list, no side effects."""
    client = TestClient(create_app())
    response = client.post("/api/chat", json={"message": "hello bot"})
    assert response.status_code == 200
    assert "Solve ticket" in response.json()["reply"]


def test_chat_approve_attempt_refused():
    """Typed approvals refuse with the safety rule (chat never decides)."""
    client = TestClient(create_app())
    response = client.post("/api/chat", json={"message": "yes, approve it"})
    assert response.status_code == 200
    assert "can't approve" in response.json()["reply"]


def test_chat_solve_unknown_ticket_404_style():
    """Solving a missing ticket answers cleanly (no task created)."""
    client = TestClient(create_app())
    response = client.post("/api/chat", json={"message": "solve ticket TCK-NOPE01"})
    assert response.status_code == 200
    assert "can't find" in response.json()["reply"]
    assert response.json()["task_id"] is None


def test_chat_solve_ticket_creates_task_and_starts_run(app_conn, monkeypatch):
    """'Solve TCK-...' creates a pending chat task and kicks its run."""
    started: dict = {}
    monkeypatch.setattr(
        chat_runner, "start_run", lambda task_id, text: started.update(task_id=task_id, text=text)
    )
    chain = _insert_ticket(app_conn, "solve")
    client = TestClient(create_app())
    response = client.post("/api/chat", json={"message": f"please solve ticket {chain['code']}"})
    assert response.status_code == 200
    body = response.json()
    assert chain["code"] in body["reply"]
    assert body["task_id"] is not None
    assert started["task_id"] == body["task_id"]
    assert chain["code"] in started["text"]
    assert chain["order_code"] in started["text"]
    assert body["actions"][0]["href"] == f"/worker/tasks/{body['task_id']}"
    task = client.get(f"/api/tasks/{body['task_id']}").json()
    assert task["status"] == "pending"
    assert task["created_by"] == "chat"


def test_chat_ticket_and_task_status(app_conn, monkeypatch):
    """Status questions summarize the ticket and the newest task."""
    monkeypatch.setattr(chat_runner, "start_run", lambda task_id, text: None)
    chain = _insert_ticket(app_conn, "status")
    client = TestClient(create_app())
    ticket = client.post("/api/chat", json={"message": chain["code"]})
    assert ticket.status_code == 200
    assert "open" in ticket.json()["reply"]
    assert ticket.json()["actions"][0]["href"] == f"/ops/tickets/{chain['code']}"
    client.post("/api/chat", json={"message": f"solve {chain['code']}"})
    latest = client.post("/api/chat", json={"message": "how is my last task doing?"})
    assert latest.status_code == 200
    assert "pending" in latest.json()["reply"]


def test_chat_list_tickets(app_conn):
    """Queue questions list open tickets with their codes."""
    chain = _insert_ticket(app_conn, "list")
    client = TestClient(create_app())
    response = client.post("/api/chat", json={"message": "show open tickets"})
    assert response.status_code == 200
    assert chain["code"] in response.json()["reply"]


def test_chat_ticket_detail_reports_order_and_policy(app_conn):
    """'Tell me about TCK-...' narrates ticket + order + refund policy."""
    chain = _insert_ticket(app_conn, "detail")
    client = TestClient(create_app())
    response = client.post("/api/chat", json={"message": f"tell me about {chain['code']}"})
    assert response.status_code == 200
    body = response.json()
    assert chain["order_code"] in body["reply"]
    assert "Refund policy" in body["reply"]
    assert any(a["kind"] == "solve" for a in body["actions"])


def test_chat_order_detail_reports_items(app_conn):
    """'Show order ORD-...' summarizes state and items with policy pointers."""
    chain = _insert_ticket(app_conn, "orderq")
    client = TestClient(create_app())
    response = client.post("/api/chat", json={"message": f"show order {chain['order_code']}"})
    assert response.status_code == 200
    assert "delivered" in response.json()["reply"]
    assert any(a["kind"] == "order" for a in response.json()["actions"])


def test_chat_order_detail_unknown_code():
    """Unknown orders answer cleanly."""
    client = TestClient(create_app())
    response = client.post("/api/chat", json={"message": "show order ORD-0000"})
    assert response.status_code == 200
    assert "can't find" in response.json()["reply"]


def test_chat_product_detail_quotes_policies():
    """'Policy for HP-01' names the product and its refund policy."""
    client = TestClient(create_app())
    response = client.post("/api/chat", json={"message": "what is the policy for HP-01?"})
    assert response.status_code == 200
    body = response.json()
    assert "Studio Headphones" in body["reply"]
    assert "Auto-approve" in body["reply"]


def test_chat_policy_answer_headlines():
    """Bare policy questions headline the refund rules."""
    client = TestClient(create_app())
    response = client.post("/api/chat", json={"message": "what is the refund policy?"})
    assert response.status_code == 200
    assert "P-REF-001" in response.json()["reply"]


def test_chat_approvals_list_empty():
    """No pending approvals answers cleanly (buttons appear when present)."""
    client = TestClient(create_app())
    response = client.post("/api/chat", json={"message": "anything waiting for approval?"})
    assert response.status_code == 200
    assert "waiting" in response.json()["reply"].lower()


def test_mark_cancelled_parks_task_instead_of_pending():
    """Background crashes land the task in `cancelled`, never stuck pending."""
    client = TestClient(create_app())
    task_id = client.post("/api/tasks", json={"text": "doomed task"}).json()["id"]
    _mark_cancelled(task_id)
    assert client.get(f"/api/tasks/{task_id}").json()["status"] == "cancelled"
