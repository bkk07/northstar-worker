"""Ticket reads."""

from app.repositories.base import BaseRepository
from database.models.biz.ticket import Ticket


class TicketRepository(BaseRepository[Ticket]):
    """Read access to `biz.tickets`."""

    def get_by_code(self, code: str) -> Ticket | None:
        """Fetch one ticket by human code."""
        return self._session.query(Ticket).filter(Ticket.code == code).one_or_none()
