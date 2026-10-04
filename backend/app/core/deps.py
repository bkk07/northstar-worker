"""FastAPI dependencies (Phase 6): DB session + ops-session guard."""

from collections.abc import Iterator

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.core.security import COOKIE_NAME, validate_session_token
from database.session import app_engine

_engine = None


def get_engine():
    """Singleton `ns_app` engine (backend role owns business writes)."""
    global _engine
    if _engine is None:
        _engine = app_engine()
    return _engine


def get_db() -> Iterator[Session]:
    """One `ns_app` session per request."""
    session = Session(bind=get_engine())
    try:
        yield session
    finally:
        session.close()


def require_ops_session(
    session: Session = Depends(get_db),
    token: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> str:
    """401 unless a live ops session cookie is present; returns agent name."""
    return validate_session_token(session, token)
