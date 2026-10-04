"""Ops session handling (Phase 6).

Sandbox auth: login inserts an `ops_sessions` row whose random UUID id is
the bearer token, carried in an httponly `ops_session` cookie. The worker
re-logs-in with a dummy agent name after SESSION_EXPIRY (Phase 18); real
auth is explicitly out of scope for the sandbox.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.repositories.ops.session_repository import SessionRepository

COOKIE_NAME = "ops_session"
SESSION_TTL = timedelta(hours=24)


def create_session(session: Session, agent_name: str) -> tuple[str, datetime]:
    """Insert a session row; return (token = row id, expiry)."""
    expires_at = datetime.now(UTC) + SESSION_TTL
    row = SessionRepository(session).create(agent_name=agent_name, expires_at=expires_at)
    session.commit()
    session.refresh(row)
    return str(row.id), expires_at


def validate_session_token(session: Session, token: str | None) -> str:
    """Return the agent name for a live token, else raise 401."""
    try:
        session_id = uuid.UUID(token) if token else None
    except (ValueError, AttributeError):
        session_id = None
    row = SessionRepository(session).get_by_id(session_id) if session_id else None
    now = datetime.now(UTC)
    if row is None or row.revoked or (row.expires_at is not None and row.expires_at < now):
        raise UnauthorizedError("ops session expired or invalid")
    return row.agent_name


def revoke_session(session: Session, token: str | None) -> None:
    """Revoke a session token (logout); missing tokens are a no-op."""
    try:
        session_id = uuid.UUID(token) if token else None
    except (ValueError, AttributeError):
        return
    if session_id is None:
        return
    SessionRepository(session).revoke(session_id)
    session.commit()
