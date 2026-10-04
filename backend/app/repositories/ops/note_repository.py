"""Ticket-note writes (internal notes and customer replies)."""

import uuid

from app.repositories.base import BaseRepository
from database.models.biz.ticket import TicketNote


class NoteRepository(BaseRepository[TicketNote]):
    """Persistence for `biz.ticket_notes`."""

    def create(
        self,
        ticket_id: uuid.UUID,
        kind: str,
        body: str,
        author: str,
        mutation_key: str,
    ) -> TicketNote:
        """Stage a note (caller commits with the log row)."""
        row = TicketNote(
            ticket_id=ticket_id,
            kind=kind,
            body=body,
            author=author,
            mutation_key=mutation_key,
        )
        self._session.add(row)
        self._session.flush()
        return row
