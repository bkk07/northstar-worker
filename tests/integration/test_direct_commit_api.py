"""Direct-commit API: token-gated service writes without the browser.

Tokens are real HMAC signatures from the agent issuer (no model involved):
valid token commits, replay returns the same entity, forged tokens 403.
Each test builds a fresh customer/order/ticket chain, so reruns never
collide on business uniqueness.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from agent.policy.issuer import issue_submit_token
from app.main import create_app
from tests.integration.conftest import make_chain
from tests.integration.conftest import staff_headers

SECRET = "local-policy-secret"


@pytest.fixture()
def client(app_conn):
    """Fresh chain + test client per test (unique entities every run)."""
    make_chain(app_conn, "direct")
    return TestClient(create_app())


def _chain_ids(app_conn) -> dict:
    """Fresh chain ids (str) for commit params."""
    chain = make_chain(app_conn, "direct")
    return {key: str(value) for key, value in chain.items()}


def _commit(client: TestClient, task_id: str, effect: str, params: dict, key: str, token: str):
    """POST one direct commit (staff JWT + HMAC submit token)."""
    from tests.integration.conftest import staff_headers

    return client.post(
        "/api/agent/direct/commits",
        headers=staff_headers(),
        json={
            "task_id": task_id,
            "effect": effect,
            "mutation_key": key,
            "token": token,
            "params": {"effect": effect, **params},
        },
    )


def _signed(task_id: str, effect: str, params: dict) -> str:
    """Real submit token for these exact params."""
    return issue_submit_token(SECRET, task_id, {"effect": effect, **params})


def test_refund_commit_and_replay(client, app_conn):
    """Valid token commits (201); same key replays the entity (200)."""
    ids = _chain_ids(app_conn)
    params = {
        "order_id": ids["order_id"],
        "ticket_id": ids["ticket_id"],
        "amount_paise": 5000,
    }
    task_id = str(uuid.uuid4())
    key = f"direct-test-{uuid.uuid4().hex[:8]}"
    first = _commit(client, task_id, "refund.create", params, key, _signed(task_id, "refund.create", params))
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["created"] is True and body["effect"] == "refund.create"

    replay = _commit(
        client, task_id, "refund.create", params, key, _signed(task_id, "refund.create", params)
    )
    assert replay.status_code == 200
    assert replay.json()["created"] is False
    assert replay.json()["entity_id"] == body["entity_id"]


def test_forged_token_rejected(client, app_conn):
    """Wrong-secret tokens 403 without touching state."""
    ids = _chain_ids(app_conn)
    params = {
        "order_id": ids["order_id"],
        "ticket_id": ids["ticket_id"],
        "amount_paise": 5000,
    }
    task_id = str(uuid.uuid4())
    forged = issue_submit_token("wrong-secret", task_id, {"effect": "refund.create", **params})
    response = _commit(client, task_id, "refund.create", params, f"direct-test-{uuid.uuid4().hex[:8]}", forged)
    assert response.status_code == 403


def test_replacement_commit(client, app_conn):
    """Replacement commits by order_item_id (201)."""
    ids = _chain_ids(app_conn)
    params = {
        "order_id": ids["order_id"],
        "ticket_id": ids["ticket_id"],
        "order_item_id": ids["item_id"],
    }
    task_id = str(uuid.uuid4())
    response = _commit(
        client, task_id, "replacement.create", params, f"direct-test-{uuid.uuid4().hex[:8]}",
        _signed(task_id, "replacement.create", params),
    )
    assert response.status_code == 201, response.text
    assert response.json()["created"] is True
