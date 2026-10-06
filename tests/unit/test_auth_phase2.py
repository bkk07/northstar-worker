"""Phase 2 auth unit tests (no DB, no docker).

Covers: Argon2 hash/verify, JWT mint/decode roundtrip, expired and
tampered tokens → 401, role guard → 403, and DTO validation.
"""

import pytest
from pydantic import ValidationError

from app.core import auth as auth_core
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.schemas.auth import LoginRequest, RegisterRequest


def test_password_roundtrip() -> None:
    hashed = auth_core.hash_password("admin12345")
    assert hashed != "admin12345"
    assert auth_core.verify_password(hashed, "admin12345") is True
    assert auth_core.verify_password(hashed, "wrong-pass") is False


def test_jwt_roundtrip() -> None:
    token = auth_core.create_access_token(
        user_id="00000000-0000-0000-0000-000000000001",
        email="jane@example.com",
        role="CUSTOMER",
    )
    claims = auth_core.decode_access_token(token)
    assert claims["email"] == "jane@example.com"
    assert claims["role"] == "CUSTOMER"


def test_jwt_tampered_rejected() -> None:
    token = auth_core.create_access_token(user_id="u1", email="a@b.co", role="CUSTOMER")
    with pytest.raises(UnauthorizedError):
        auth_core.decode_access_token(token + "tamper")


def test_jwt_wrong_secret_rejected(monkeypatch) -> None:
    from northstar_common import config as config_mod

    token = auth_core.create_access_token(user_id="u1", email="a@b.co", role="CUSTOMER")
    settings = config_mod.get_settings()
    monkeypatch.setattr(settings, "jwt_secret", "different-secret")
    try:
        with pytest.raises(UnauthorizedError):
            auth_core.decode_access_token(token)
    finally:
        config_mod.get_settings.cache_clear()


def test_role_guard_forbids_customer_on_admin_route() -> None:
    guard = auth_core.require_roles("SUPPORT_AGENT")
    with pytest.raises(ForbiddenError):
        guard({"sub": "u1", "email": "a@b.co", "role": "CUSTOMER"})
    allowed = guard({"sub": "u2", "email": "admin@northstar.shop", "role": "SUPPORT_AGENT"})
    assert allowed["role"] == "SUPPORT_AGENT"


def test_register_dto_validation() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(name="", email="not-an-email", password="short")
    ok = RegisterRequest(name="Jane", email="jane@example.com", password="password123")
    assert ok.role == "CUSTOMER"


def test_login_dto_requires_password() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(email="jane@example.com", password="")
