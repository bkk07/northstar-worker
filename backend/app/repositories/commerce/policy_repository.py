"""Policy reads."""

from app.repositories.base import BaseRepository
from database.models.biz.policy import Policy


class PolicyRepository(BaseRepository[Policy]):
    """Read access to `biz.policies`."""

    def list_all(self) -> list[Policy]:
        """All policy rules ordered by key."""
        return self._session.query(Policy).order_by(Policy.rule_key).all()
