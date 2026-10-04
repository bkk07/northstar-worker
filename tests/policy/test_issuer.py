"""Token issuer + guard: real commit authority end to end (Phase 15).

The issuer signs what the guard verifies, over the same stripped surface.
Operational keys (refs, keys, tokens) never affect authority, so
re-discovered refs keep working while tampered bindings fail.
"""

from agent.contract.action_validator import SUBMIT_OPERATIONAL_KEYS
from agent.policy.issuer import SUBMIT_ACTION, issue_submit_token, signable_params
from mcp_server.token_guard import OPERATIONAL_KEYS, TokenDenied, verify_submit_token

SECRET = "test-secret"
TASK = "task-1"
PARAMS = {
    "effect": "replacement.create",
    "order_id": "o-1942",
    "order_item_id": "i-1",
    "ticket_id": "t-101",
}


def test_issued_token_verifies():
    """ALLOW-time issuance is exactly what the commit gate accepts."""
    token = issue_submit_token(SECRET, TASK, PARAMS)
    verify_submit_token(token, SECRET, TASK, dict(PARAMS))


def test_ref_changes_keep_authority():
    """Re-discovered refs do not invalidate the token (recovery-safe)."""
    token = issue_submit_token(SECRET, TASK, {**PARAMS, "ref": "e3"})
    verify_submit_token(token, SECRET, TASK, {**PARAMS, "ref": "e99"})


def test_tampered_bindings_rejected():
    """Any binding change breaks the signature (fail closed)."""
    token = issue_submit_token(SECRET, TASK, PARAMS)
    for bad in (
        {**PARAMS, "order_id": "o-9999"},
        {**PARAMS, "amount_paise": 1},
        {**PARAMS, "effect": "refund.create"},
    ):
        try:
            verify_submit_token(token, SECRET, TASK, bad)
        except TokenDenied:
            continue
        raise AssertionError(f"tampered params accepted: {bad}")


def test_wrong_secret_or_task_rejected():
    """Cross-secret and cross-task tokens are worthless."""
    token = issue_submit_token(SECRET, TASK, PARAMS)
    for args in (
        (token, "other-secret", TASK, PARAMS),
        (token, SECRET, "other-task", PARAMS),
        ("bogus", SECRET, TASK, PARAMS),
    ):
        try:
            verify_submit_token(*args)
        except TokenDenied:
            continue
        raise AssertionError(f"bad token accepted: {args[1:3]}")


def test_operational_surfaces_match():
    """Issuer and guard strip the same keys (drift breaks recovery)."""
    assert set(OPERATIONAL_KEYS) == set(SUBMIT_OPERATIONAL_KEYS)
    assert SUBMIT_ACTION == "browser_submit"
    assert signable_params({**PARAMS, "ref": "e1", "token": "t"}) == PARAMS
