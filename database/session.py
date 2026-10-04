"""Per-role engine/session factories (schema only, no business logic).

Roles (Phase 4 grants):
- `postgres` (superuser): migrations only, via DATABASE_URL.
- `ns_app`: writes `biz.*`, API-owned `worker.*` rows.
- `ns_runner`: writes `worker.*`, reads `biz` through `worker.v_*` views.
- `ns_verifier`: SELECT-only everywhere.
- `ns_test_redteam`: test-only writer of bad states for verifier red-team.

Role passwords are local-dev parity (`northstar`); override every URL
with NS_*_DATABASE_URL env vars anywhere else.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

_DEFAULT_BASE = "postgresql+psycopg://{user}:northstar@localhost:5433/northstar"

ROLE_URL_ENV = {
    "admin": "DATABASE_URL",
    "ns_app": "NS_APP_DATABASE_URL",
    "ns_runner": "NS_RUNNER_DATABASE_URL",
    "ns_verifier": "NS_VERIFIER_DATABASE_URL",
    "ns_test_redteam": "NS_REDTEAM_DATABASE_URL",
}

ROLE_DEFAULT_USER = {
    "admin": "postgres:postgres",
    "ns_app": "ns_app",
    "ns_runner": "ns_runner",
    "ns_verifier": "ns_verifier",
    "ns_test_redteam": "ns_test_redteam",
}


def role_url(role: str) -> str:
    """Connection URL for a role (env override or local default)."""
    env_var = ROLE_URL_ENV[role]
    if env_var in os.environ:
        return os.environ[env_var]
    user = ROLE_DEFAULT_USER[role]
    if role == "admin":
        return "postgresql+psycopg://postgres:postgres@localhost:5433/northstar"
    return _DEFAULT_BASE.format(user=user)


def create_role_engine(role: str) -> Engine:
    """Engine for a role (NullPool: one short-lived connection per use)."""
    from sqlalchemy.pool import NullPool

    return create_engine(role_url(role), poolclass=NullPool)


def admin_engine() -> Engine:
    """Superuser engine (migrations and test setup only)."""
    return create_role_engine("admin")


def app_engine() -> Engine:
    """`ns_app` engine (backend services)."""
    return create_role_engine("ns_app")


def runner_engine() -> Engine:
    """`ns_runner` engine (agent repositories)."""
    return create_role_engine("ns_runner")


def verifier_engine() -> Engine:
    """`ns_verifier` engine (read-only verification)."""
    return create_role_engine("ns_verifier")


def redteam_engine() -> Engine:
    """`ns_test_redteam` engine (verifier red-team tests only)."""
    return create_role_engine("ns_test_redteam")


def session_for(engine: Engine) -> Session:
    """One Session from an engine (caller owns close/commit)."""
    return sessionmaker(bind=engine, expire_on_commit=False)()
