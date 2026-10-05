"""Phase 9: control plane + deterministic fault injection (live DB)."""

import os
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_app
from database.seeds import loader
from database.session import admin_engine

OPERATOR_TOKEN = os.environ.get("OPERATOR_TOKEN", "local-operator-token")


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {OPERATOR_TOKEN}"}


def _key(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@pytest.fixture()
def client():
    """Seeded world + logged-in client, faults cleared after each test."""
    loader.seed()
    client = TestClient(create_app())
    assert client.post("/api/ops/auth/login", json={"agent_name": "phase9"}).status_code == 200
    yield client
    with admin_engine().begin() as conn:
        conn.execute(text("DELETE FROM biz.fault_plans"))


def _arm(client, fault_type, target, trigger=None, params=None):
    response = client.post(
        "/api/control/chaos",
        json={
            "fault_type": fault_type,
            "target": target,
            "trigger": trigger or {"nth_call": 1},
            "params": params or {},
        },
        headers=_auth(),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _fresh_order_ticket(client, customer_code="C112"):
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
    shop = TestClient(create_app())
    created = shop.post(
        "/api/shop/tickets",
        json={
            "customer_code": customer_code,
            "order_code": order_code,
            "subject": "Phase 9 probe",
            "body": "Probe.",
            "category": "damage",
        },
    )
    assert created.status_code == 201
    return order_code, sku, created.json()["code"]


def _row_count(table, key) -> int:
    with admin_engine().connect() as conn:
        return conn.execute(
            text(f"SELECT count(*) FROM {table} WHERE mutation_key = :key"), {"key": key}
        ).scalar()


def test_chaos_requires_operator_token():
    """No token: 401. Wrong token: 403."""
    bare = TestClient(create_app())
    assert bare.post("/api/control/chaos", json={}).status_code in (401, 422)
    no_auth = TestClient(create_app())
    response = no_auth.post(
        "/api/control/chaos",
        json={"fault_type": "TIMEOUT", "target": "ops.notes"},
    )
    assert response.status_code == 401
    wrong = TestClient(create_app())
    response = wrong.post(
        "/api/control/chaos",
        json={"fault_type": "TIMEOUT", "target": "ops.notes"},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 403


def test_arm_rejects_unknown_fault_and_target(client):
    """Arming validates type and target (422)."""
    bad_type = client.post(
        "/api/control/chaos",
        json={"fault_type": "NOPE", "target": "ops.notes"},
        headers=_auth(),
    )
    assert bad_type.status_code == 422
    bad_target = client.post(
        "/api/control/chaos",
        json={"fault_type": "TIMEOUT", "target": "ops.unknown"},
        headers=_auth(),
    )
    assert bad_target.status_code == 422


def test_500_before_commit_writes_nothing(client):
    """500 before commit: error out, no row, no log; consumed after firing."""
    order_code, sku, ticket_code = _fresh_order_ticket(client)
    _arm(client, "HTTP_500_BEFORE_COMMIT", "ops.replacements")
    key = _key("f9")
    response = client.post(
        "/api/ops/replacements",
        json={"order_code": order_code, "item_sku": sku, "ticket_code": ticket_code},
        headers={"Idempotency-Key": key},
    )
    assert response.status_code == 500
    assert _row_count("biz.replacements", key) == 0
    assert _row_count("biz.mutation_log", key) == 0
    retry = client.post(
        "/api/ops/replacements",
        json={"order_code": order_code, "item_sku": sku, "ticket_code": ticket_code},
        headers={"Idempotency-Key": key},
    )
    assert retry.status_code == 201


def test_nth_call_trigger_deterministic(client):
    """nth_call 2: first call clean, second call faulted."""
    _arm(client, "HTTP_500_BEFORE_COMMIT", "ops.notes", trigger={"nth_call": 2})
    first = client.post(
        "/api/ops/tickets/TCK-140/notes",
        json={"kind": "internal", "body": "first"},
        headers={"Idempotency-Key": _key("f9")},
    )
    assert first.status_code == 201
    second = client.post(
        "/api/ops/tickets/TCK-140/notes",
        json={"kind": "internal", "body": "second"},
        headers={"Idempotency-Key": _key("f9")},
    )
    assert second.status_code == 500


def test_500_after_commit_leaves_row(client):
    """500 after commit: the client sees 500 but the row (and log) exist."""
    order_code, sku, ticket_code = _fresh_order_ticket(client)
    _arm(client, "HTTP_500_AFTER_COMMIT", "ops.replacements")
    key = _key("f9")
    response = client.post(
        "/api/ops/replacements",
        json={"order_code": order_code, "item_sku": sku, "ticket_code": ticket_code},
        headers={"Idempotency-Key": key},
    )
    assert response.status_code == 500
    assert _row_count("biz.replacements", key) == 1
    assert _row_count("biz.mutation_log", key) == 1
    probe = client.get(f"/api/read/probe/mutation/{key}").json()
    assert probe["found"] is True
    assert probe["kind"] == "replacement"


def test_duplicate_effect_ignores_key_once(client):
    """Same key retried under the fault: 409 (not a 200 replay), one row."""
    order_code, sku, ticket_code = _fresh_order_ticket(client)
    key = _key("f9")
    payload = {"order_code": order_code, "item_sku": sku, "ticket_code": ticket_code}
    assert (
        client.post(
            "/api/ops/replacements", json=payload, headers={"Idempotency-Key": key}
        ).status_code
        == 201
    )
    _arm(client, "DUPLICATE_EFFECT", "ops.replacements")
    retry = client.post("/api/ops/replacements", json=payload, headers={"Idempotency-Key": key})
    assert retry.status_code == 409
    assert _row_count("biz.replacements", key) == 1
    assert client.get(f"/api/read/probe/mutation/{key}").json()["found"] is True


def test_validation_error_then_success_same_key(client):
    """Faulted submit 422s with a field message; the same key then works."""
    order_code, sku, ticket_code = _fresh_order_ticket(client)
    _arm(
        client,
        "VALIDATION_ERROR",
        "ops.replacements",
        params={"field": "item_sku", "message": "SKU-XYZ is unknown"},
    )
    key = _key("f9")
    payload = {"order_code": order_code, "item_sku": sku, "ticket_code": ticket_code}
    rejected = client.post("/api/ops/replacements", json=payload, headers={"Idempotency-Key": key})
    assert rejected.status_code == 422
    assert "SKU-XYZ" in rejected.json()["message"]
    accepted = client.post("/api/ops/replacements", json=payload, headers={"Idempotency-Key": key})
    assert accepted.status_code == 201


def test_timeout_delays_past_client_deadline(client):
    """TIMEOUT sleeps past the deadline; the committed row still exists."""
    _arm(
        client,
        "TIMEOUT",
        "ops.notes",
        params={"delay_seconds": 2, "after_commit": True},
    )
    key = _key("f9")
    started = time.monotonic()
    response = client.post(
        "/api/ops/tickets/TCK-140/notes",
        json={"kind": "internal", "body": "slow note"},
        headers={"Idempotency-Key": key},
    )
    elapsed = time.monotonic() - started
    assert elapsed >= 1.9
    assert response.status_code == 201
    assert _row_count("biz.mutation_log", key) == 1


def test_session_expiry_revokes_mid_run(client):
    """The faulted call 401s; reads 401 too until a fresh login."""
    _arm(client, "SESSION_EXPIRY", "ops.notes")
    faulted = client.post(
        "/api/ops/tickets/TCK-140/notes",
        json={"kind": "internal", "body": "x"},
        headers={"Idempotency-Key": _key("f9")},
    )
    assert faulted.status_code == 401
    assert client.get("/api/ops/tickets").status_code == 401
    assert (
        client.post("/api/ops/auth/login", json={"agent_name": "phase9-again"}).status_code == 200
    )
    assert client.get("/api/ops/tickets", params={"page": 1}).status_code == 200


def test_reset_clears_armed_faults(client):
    """Reset truncates fault plans (and the world)."""
    _arm(client, "TIMEOUT", "ops.notes")
    _arm(client, "DOM_DRIFT", "ops.customer_search")
    assert client.get("/api/ops/ui-flags").json()["dom_drift"] is True
    reset = client.post("/api/control/reset", headers=_auth())
    assert reset.status_code == 200
    assert reset.json()["ok"] is True
    loader.seed()
    # Reset truncates sessions too: log back in before reading flags.
    assert client.post("/api/ops/auth/login", json={"agent_name": "phase9"}).status_code == 200
    assert client.get("/api/ops/ui-flags").json() == {
        "removed_search_field": False,
        "dom_drift": False,
        "stale_rerender": False,
    }


def test_seed_and_oracle_endpoints(client):
    """Seed returns counts+hash; oracle derives per scenario and ticket."""
    seeded = client.post("/api/control/seed", headers=_auth())
    assert seeded.status_code == 200
    assert seeded.json()["counts"]["tickets"] == 60
    assert len(seeded.json()["world_hash"]) == 64
    hero = client.get("/api/control/oracle/S1", headers=_auth()).json()
    assert hero["expected_outcome"] == "AUTO_RESOLVE"
    assert hero["expected_effects"][0]["effect"] == "replacement.create"
    injection = client.get("/api/control/oracle/TCK-105", headers=_auth()).json()
    assert injection["scenario_id"] == "S5"
    assert injection["expected_outcome"] == "BLOCK"
    assert injection["expected_effects"] == []
    assert client.get("/api/control/oracle/NOPE", headers=_auth()).status_code == 404
