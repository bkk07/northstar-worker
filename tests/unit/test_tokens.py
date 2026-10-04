"""Phase 3: HMAC policy tokens sign, verify, and fail closed on tamper."""

import pytest

from northstar_common.tokens import PolicyToken, sign_policy_token, verify_policy_token

SECRET = "test-secret"
TASK = "11111111-2222-3333-4444-555555555555"
ACTION = "browser_submit"
PARAMS_HASH = "a" * 64


def test_sign_verify_roundtrip():
    token = sign_policy_token(SECRET, TASK, ACTION, PARAMS_HASH)
    assert verify_policy_token(token, SECRET, TASK, ACTION, PARAMS_HASH)


def test_tampered_signature_rejected():
    token = sign_policy_token(SECRET, TASK, ACTION, PARAMS_HASH)
    tampered = token[:-1] + ("0" if token[-1] != "0" else "1")
    assert not verify_policy_token(tampered, SECRET, TASK, ACTION, PARAMS_HASH)


def test_wrong_secret_rejected():
    token = sign_policy_token(SECRET, TASK, ACTION, PARAMS_HASH)
    assert not verify_policy_token(token, "other-secret", TASK, ACTION, PARAMS_HASH)


def test_wrong_binding_rejected():
    token = sign_policy_token(SECRET, TASK, ACTION, PARAMS_HASH)
    assert not verify_policy_token(token, SECRET, "other-task", ACTION, PARAMS_HASH)
    assert not verify_policy_token(token, SECRET, TASK, ACTION, "b" * 64)


@pytest.mark.parametrize("raw", ["", "abc", "a:b:c", "a:b:c:d:e", ":::"])
def test_malformed_tokens_rejected(raw: str):
    assert not verify_policy_token(raw, SECRET, TASK, ACTION, PARAMS_HASH)
    if raw not in ("",):
        with pytest.raises(ValueError):
            PolicyToken.decode(raw)
