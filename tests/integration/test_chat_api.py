"""Chat endpoint: intent routing over live Postgres (run launch stubbed)."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_app
from app.services.worker import chat_runner
from app.services.worker.chat_runner import _mark_cancelled


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


def test_mark_cancelled_parks_task_instead_of_pending():
    """Background crashes land the task in `cancelled`, never stuck pending."""
    client = TestClient(create_app())
    task_id = client.post("/api/tasks", json={"text": "doomed task"}).json()["id"]
    _mark_cancelled(task_id)
    assert client.get(f"/api/tasks/{task_id}").json()["status"] == "cancelled"
