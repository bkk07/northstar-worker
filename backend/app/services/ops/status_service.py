"""Ticket status mutation service (idempotent)."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.ops.mutation_repository import MutationRepository
from app.repositories.ops.ticket_repository import TicketRepository
from app.schemas.commerce.ticket import TicketRead
from app.schemas.ops.notes import StatusUpdate
from app.services.commerce.ticket_service import to_ticket_dto

KIND = "ticket_status"


class StatusService:
    """Change-or-replay ticket status."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._mutations = MutationRepository(session)
        self._tickets = TicketRepository(session)

    def update(
        self, ticket_code: str, payload: StatusUpdate, idempotency_key: str
    ) -> tuple[TicketRead, bool]:
        """Set ticket status, or replay the prior change."""
        prior = self._mutations.find_by_key(idempotency_key)
        ticket = self._tickets.get_by_code(ticket_code)
        if ticket is None:
            raise NotFoundError(f"ticket {ticket_code} not found")
        if prior is not None:
            if prior.kind != KIND:
                raise ConflictError(f"idempotency key already used for {prior.kind}")
            return to_ticket_dto(ticket), False
        try:
            self._tickets.set_status(ticket, payload.to_status)
            self._mutations.record(idempotency_key, KIND, ticket.id)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("duplicate status change") from exc
        return to_ticket_dto(ticket), True
