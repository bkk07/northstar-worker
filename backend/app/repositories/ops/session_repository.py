"""Ops session rows."""

import uuid
from datetime import datetime

from app.repositories.base import BaseRepository
from database.models.biz.ops import OpsSession


class SessionRepository(BaseRepository[OpsSession]):
    """Persistence for `biz.ops_sessions`."""

    def create(self, agent_name: str, expires_at: datetime) -> OpsSession:
        """Insert a session row (id is the bearer token)."""
        row = OpsSession(agent_name=agent_name, expires_at=expires_at, revoked=False)
        self._session.add(row)
        self._session.flush()
        return row

    def get_by_id(self, session_id: uuid.UUID) -> OpsSession | None:
        """Fetch a session by its token id."""
        return self._session.get(OpsSession, session_id)

    def revoke(self, session_id: uuid.UUID) -> None:
        """Mark a session revoked (logout / session-expiry fault)."""
        row = self.get_by_id(session_id)
        if row is not None:
            row.revoked = True
            self._session.flush()
