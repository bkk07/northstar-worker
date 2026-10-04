"""Phase 6: ops API — auth, idempotency, and business-rule mapping (live DB)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_app
from database.seeds import loader
from database.session import admin_engine


def _key(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@pytest.fixture(scope="module")
def client():
    """Seeded world + logged-in client (cookie persists across calls)."""
    loader.seed()
    client = TestClient(create_app())
    response = client.post("/api/ops/auth/login", json={"agent_name": "phase6-probe"})
    assert response.status_code == 200
    return client


def _raise_ticket(client, customer_code, order_code) -> str:
    response = client.post(
        "/api/shop/tickets",
        json={
            "customer_code": customer_code,
            "order_code": order_code,
            "subject": "Phase 6 probe ticket",
            "body": "Probe ticket for mutation tests.",
            "category": "damage",
        },
    )
    assert response.status_code == 201
    return response.json()["code"]


def _fresh_order_ticket(client, customer_code: str) -> tuple[str, str, str]:
    """Unique order + item + ticket per run (tests stay re-runnable)."""
    order_code = f"O-{uuid.uuid4().hex[:8].upper()}"
    sku = f"SKU-{uuid.uuid4().hex[:6].upper()}"
    with admin_engine().begin() as conn:
        customer_id = conn.execute(
            text("SELECT id FROM biz.customers WHERE code = :code"),
            {"code": customer_code},
        ).scalar_one()
        order_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO biz.orders (id, code, customer_id, status, total_paise, "
                "paid_paise, placed_at) VALUES (:id, :code, :cid, 'delivered', "
                "1000000, 1000000, now())"
            ),
            {"id": order_id, "code": order_code, "cid": customer_id},
        )
        conn.execute(
            text(
                "INSERT INTO biz.order_items (id, order_id, sku, title, qty, unit_paise, "
                "category) VALUES (:id, :oid, :sku, 'Probe Widget', 1, 1000000, 'home')"
            ),
            {"id": uuid.uuid4(), "oid": order_id, "sku": sku},
        )
    return order_code, sku, _raise_ticket(client, customer_code, order_code)


def test_unauthenticated_ops_post_401():
    """No session cookie: 401 with the UNAUTHORIZED code."""
    bare = TestClient(create_app())
    response = bare.post(
        "/api/ops/replacements",
        json={"order_code": "ORD-1950", "item_sku": "CB-05", "ticket_code": "TCK-111"},
        headers={"Idempotency-Key": _key("k")},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_missing_idempotency_key_422(client):
    """Ops POSTs require the Idempotency-Key header."""
    response = client.post(
        "/api/ops/replacements",
        json={"order_code": "ORD-1950", "item_sku": "CB-05", "ticket_code": "TCK-111"},
    )
    assert response.status_code == 422


def test_replacement_idempotent_same_key_returns_same_entity(client):
    """Same key twice: 201 then 200, one row, one log row."""
    order_code, sku, ticket_code = _fresh_order_ticket(client, "C112")
    key = _key("phase6-repl")
    payload = {"order_code": order_code, "item_sku": sku, "ticket_code": ticket_code}
    first = client.post("/api/ops/replacements", json=payload, headers={"Idempotency-Key": key})
    assert first.status_code == 201
    second = client.post("/api/ops/replacements", json=payload, headers={"Idempotency-Key": key})
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    with admin_engine().connect() as conn:
        rows = conn.execute(
            text("SELECT count(*) FROM biz.replacements WHERE mutation_key = :key"),
            {"key": key},
        ).scalar()
        logs = conn.execute(
            text("SELECT count(*) FROM biz.mutation_log WHERE mutation_key = :key"),
            {"key": key},
        ).scalar()
    assert rows == 1
    assert logs == 1


def test_replacement_duplicate_identity_409(client):
    """Different key, same active item: 409."""
    order_code, sku, ticket_code = _fresh_order_ticket(client, "C113")
    payload = {"order_code": order_code, "item_sku": sku, "ticket_code": ticket_code}
    first = client.post(
        "/api/ops/replacements", json=payload, headers={"Idempotency-Key": _key("k")}
    )
    assert first.status_code == 201
    second = client.post(
        "/api/ops/replacements", json=payload, headers={"Idempotency-Key": _key("k")}
    )
    assert second.status_code == 409
    assert second.json()["code"] == "CONFLICT"


def test_refund_over_paid_422(client):
    """Refund above paid is a 422 (backend rule, before worker policy)."""
    response = client.post(
        "/api/ops/refunds",
        json={"order_code": "ORD-1956", "ticket_code": "TCK-117", "amount_paise": 600000},
        headers={"Idempotency-Key": _key("k")},
    )
    assert response.status_code == 422


def test_ownership_mismatch_422(client):
    """Ticket and order from different customers: 422."""
    response = client.post(
        "/api/ops/replacements",
        json={"order_code": "ORD-1959", "item_sku": "CM-14", "ticket_code": "TCK-120"},
        headers={"Idempotency-Key": _key("k")},
    )
    assert response.status_code == 422


def test_note_reply_status_flows_with_replay(client):
    """Notes, replies, and status changes create once and replay."""
    note = client.post(
        "/api/ops/tickets/TCK-140/notes",
        json={"kind": "internal", "body": "Phase 6 note"},
        headers={"Idempotency-Key": _key("k")},
    )
    assert note.status_code == 201
    replay = client.post(
        "/api/ops/tickets/TCK-140/notes",
        json={"kind": "internal", "body": "Phase 6 note"},
        headers={"Idempotency-Key": note.json()["mutation_key"]},
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == note.json()["id"]

    reply_key = _key("k")
    reply = client.post(
        "/api/ops/tickets/TCK-127/reply",
        json={"body": "Your replacement ships tomorrow."},
        headers={"Idempotency-Key": reply_key},
    )
    assert reply.status_code == 201
    assert reply.json()["kind"] == "customer_reply"

    status_key = _key("k")
    changed = client.post(
        "/api/ops/tickets/TCK-128/status",
        json={"to_status": "resolved"},
        headers={"Idempotency-Key": status_key},
    )
    assert changed.status_code == 201
    assert changed.json()["status"] == "resolved"
    again = client.post(
        "/api/ops/tickets/TCK-128/status",
        json={"to_status": "resolved"},
        headers={"Idempotency-Key": status_key},
    )
    assert again.status_code == 200


def test_ticket_queue_paginated(client):
    """Queue honors page size with a total."""
    body = client.get("/api/ops/tickets", params={"page": 1, "page_size": 10}).json()
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert len(body["items"]) == 10
    assert body["total"] >= 45


def test_ui_flags_default_off(client):
    """No armed faults: every UI flag is false."""
    assert client.get("/api/ops/ui-flags").json() == {
        "removed_search_field": False,
        "dom_drift": False,
        "stale_rerender": False,
    }


def test_logout_releases_session(client):
    """Logout revokes the session; further mutation calls are 401."""
    assert client.post("/api/ops/auth/logout").status_code == 200
    response = client.post(
        "/api/ops/tickets/TCK-140/notes",
        json={"kind": "internal", "body": "after logout"},
        headers={"Idempotency-Key": _key("k")},
    )
    assert response.status_code == 401
