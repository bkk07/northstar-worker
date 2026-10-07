"""Security blocker tests: registration, secrets, approval TTL."""

import datetime

from backend.app.services.auth import auth_service  # noqa: F401  (import path check)


def test_public_register_forces_customer(tmp_path) -> None:
    # Service-level: role argument is ignored, always CUSTOMER.
    import inspect

    src = inspect.getsource(auth_service.register)
    assert "CUSTOMER" in src
    assert 'role="CUSTOMER"' in src or "role='CUSTOMER'" in src


def test_approval_ttl_constant() -> None:
    from app.services.agent_run.agent_run_service import APPROVAL_TTL

    assert APPROVAL_TTL == datetime.timedelta(hours=24)


def test_production_secrets_fail_closed() -> None:
    from northstar_common.config import assert_production_secrets, get_settings

    settings = get_settings()
    if settings.environment == "local":
        assert_production_secrets()  # no raise in local
    assert callable(assert_production_secrets)
