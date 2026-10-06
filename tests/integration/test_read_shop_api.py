"""Phase 6: read + shop API contract tests (live DB, seeded world)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from database.seeds import loader


@pytest.fixture(scope="module")
def client():
    """Seeded world + test client (module-scoped, read-mostly)."""
    loader.seed()
    return TestClient(create_app())


def test_search_customers_finds_look_alikes(client):
    """q=Priya returns both Nair and Nayar."""
    body = client.get("/api/read/customers", params={"q": "Priya"}).json()
    assert {c["code"] for c in body} >= {"C105", "C106"}


def test_order_detail_shape(client):
    """Order read carries items and paise amounts."""
    customers = client.get("/api/read/customers", params={"q": "Aarav Sharma"}).json()
    customer_id = customers[0]["id"]
    orders = client.get("/api/read/orders", params={"customer_id": customer_id}).json()
    order = next(o for o in orders if o["code"] == "ORD-1942")
    assert order["total_paise"] == 8500000
    assert order["items"][0]["sku"] == "LAP-X1"
    detail = client.get(f"/api/read/orders/{order['id']}").json()
    assert detail["code"] == "ORD-1942"


def test_ticket_and_policies_shape(client):
    """Ticket read and the 14 seeded policy rows."""
    ticket_id = client.get("/api/shop/tickets/TCK-101").json()["id"]
    ticket = client.get(f"/api/read/tickets/{ticket_id}").json()
    assert ticket["code"] == "TCK-101"
    assert ticket["status"] == "open"
    policies = client.get("/api/read/policies").json()
    assert len(policies) == 14
    assert {p["rule_key"] for p in policies} >= {"P-REF-001", "P-REPL-001"}


def test_order_tickets_lists_linked_tickets(client):
    """Order detail endpoint lists the tickets raised against it."""
    body = client.get("/api/shop/orders/ORD-1943/tickets").json()
    assert {t["code"] for t in body} >= {"TCK-102", "TCK-105"}
    assert all(t["order_id"] for t in body)


def test_order_tickets_unknown_order_404s(client):
    """Unknown orders 404 instead of returning an empty list."""
    assert client.get("/api/shop/orders/ORD-0000/tickets").status_code == 404


def test_probe_missing_and_found(client):
    """Absent keys report found=false; history keys report identity."""
    missing = client.get("/api/read/probe/mutation/does-not-exist").json()
    assert missing == {"found": False, "kind": None, "entity_id": None}
    found = client.get("/api/read/probe/mutation/hist-k1").json()
    assert found["found"] is True
    assert found["kind"] == "refund"


def test_read_api_rejects_post(client):
    """Reads are GET-only: POST returns 405."""
    response = client.post("/api/read/orders", params={"customer_id": str(uuid.uuid4())})
    assert response.status_code == 405


def test_refunds_by_customer_window(client):
    """Repeat-refunder facts: C107's four settled refunds come back."""
    customers = client.get("/api/read/customers", params={"q": "C107"}).json()
    customer_id = next(c["id"] for c in customers if c["code"] == "C107")
    body = client.get(
        "/api/read/refunds", params={"customer_id": customer_id, "window_days": 90}
    ).json()
    assert len(body) == 4
    assert {r["amount_paise"] for r in body} == {50000, 75000, 60000, 90000}


def test_refunds_by_order_for_duplicate_trap(client):
    """Order-wide active refunds expose same-amount double refunds."""
    order_id = client.get("/api/shop/orders/ORD-1973").json()["id"]
    body = client.get("/api/read/refunds", params={"order_id": order_id}).json()
    assert len(body) == 1
    assert body[0]["amount_paise"] == 90000


def test_refunds_require_exactly_one_scope(client):
    """Zero or two scopes are 422 (fail closed on ambiguous reads)."""
    assert client.get("/api/read/refunds").status_code == 422
    response = client.get(
        "/api/read/refunds",
        params={"ticket_id": str(uuid.uuid4()), "customer_id": str(uuid.uuid4())},
    )
    assert response.status_code == 422


def test_read_unknown_ids_404(client):
    """Unknown entities map to 404 with the NOT_FOUND code."""
    missing = str(uuid.uuid4())
    for path in (
        f"/api/read/customers/{missing}",
        f"/api/read/orders/{missing}",
        f"/api/read/tickets/{missing}",
    ):
        response = client.get(path)
        assert response.status_code == 404, path
        assert response.json()["code"] == "NOT_FOUND"


def test_shop_orders_and_raise_ticket(client):
    """Customer views orders and raises a ticket that persists."""
    orders = client.get("/api/shop/orders", params={"customer_code": "C101"}).json()
    assert {o["code"] for o in orders} >= {"ORD-1942", "ORD-1955", "ORD-1974"}
    created = client.post(
        "/api/shop/tickets",
        json={
            "customer_code": "C101",
            "order_code": "ORD-1942",
            "subject": "Screen flicker follow-up",
            "body": "The flicker is back on the replacement unit.",
            "category": "damage",
        },
    )
    assert created.status_code == 201
    code = created.json()["code"]
    fetched = client.get(f"/api/shop/tickets/{code}").json()
    assert fetched["status"] == "open"
    assert fetched["body"].startswith("The flicker")
