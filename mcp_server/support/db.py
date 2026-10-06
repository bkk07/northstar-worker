"""DB sessions for support tools (spec Phase 7).

Tools never touch SQL: they open a session here and hand it to the backend
service layer (`app.services.*`), the same safe operations the REST API
uses. The factory override exists so unit tests can inject fakes without
a database.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

_factory = None


def set_session_factory(fn) -> None:
    """Override session creation (tests only)."""
    global _factory
    _factory = fn


@contextmanager
def support_session() -> Iterator[Session]:
    """One short-lived `ns_app` session per tool call."""
    if _factory is not None:
        yield _factory()
        return
    from database.session import app_engine, session_for

    session = session_for(app_engine())
    try:
        yield session
    finally:
        session.close()
