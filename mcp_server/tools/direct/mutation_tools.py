"""Direct commit tools: service-layer writes without the browser.

Same authority as `browser_submit` (capability + HMAC submit token over
the exact params, same idempotency key), executed as one backend call
instead of a Chromium form flow. Transport failures raise (retryable);
HTTP outcomes (201/200/409/422) return as data for the classifier.
"""

import os

import httpx

from mcp_server import context
from mcp_server.schemas.tools import DirectCommitInput

_COMMIT_PATH = "/api/agent/direct/commits"


def _post_commit(task_id: str, effect: str, mutation_key: str, token: str, params: dict) -> dict:
    """One token-authorized commit against the backend direct endpoint."""
    args = DirectCommitInput(
        task_id=task_id, mutation_key=mutation_key, token=token, params=params
    )
    context.store().check(args.task_id, effect)
    base_url = os.environ.get(context.READ_API_URL_ENV, "http://127.0.0.1:8000")
    try:
        response = httpx.Client(base_url=base_url.rstrip("/"), timeout=20.0).post(
            _COMMIT_PATH,
            headers={"Authorization": f"Bearer {context.service_token()}"},
            json={
                "task_id": args.task_id,
                "effect": effect,
                "mutation_key": args.mutation_key,
                "token": args.token,
                "params": args.params,
            },
        )
    except httpx.HTTPError as exc:
        raise RuntimeError(f"direct {effect} transport error: {exc}") from exc
    if response.status_code >= 400:
        return {
            "ok": False,
            "status": response.status_code,
            "effect": effect,
            "mutation_key": args.mutation_key,
            "error": response.text[:500],
        }
    body = response.json()
    return {
        "ok": True,
        "status": body.get("status", 201),
        "effect": effect,
        "mutation_key": args.mutation_key,
        "created": body.get("created", True),
        "entity_id": body.get("entity_id"),
    }


def refund_create(task_id: str, mutation_key: str, token: str, params: dict) -> dict:
    """Commit a refund via the service layer (no browser)."""
    return _post_commit(task_id, "refund.create", mutation_key, token, params)


def replacement_create(task_id: str, mutation_key: str, token: str, params: dict) -> dict:
    """Commit a replacement via the service layer (no browser)."""
    return _post_commit(task_id, "replacement.create", mutation_key, token, params)
