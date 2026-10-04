"""Note and reply mutation service (idempotent)."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.ops.mutation_repository import MutationRepository
from app.repositories.ops.note_repository import NoteRepository
from app.repositories.ops.ticket_repository import TicketRepository
from app.schemas.ops.notes import NoteCreate, NoteRead, ReplyCreate
from database.models.biz.ticket import TicketNote

NOTE_KIND = "ticket_note"
REPLY_KIND = "ticket_reply"


class NoteService:
    """Create-or-replay internal notes and customer replies."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._mutations = MutationRepository(session)
        self._notes = NoteRepository(session)
        self._tickets = TicketRepository(session)

    def create_note(
        self, ticket_code: str, payload: NoteCreate, idempotency_key: str
    ) -> tuple[NoteRead, bool]:
        """Attach an internal note, or replay the prior one."""
        return self._create(ticket_code, NOTE_KIND, payload.body, payload.author, idempotency_key)

    def create_reply(
        self, ticket_code: str, payload: ReplyCreate, idempotency_key: str
    ) -> tuple[NoteRead, bool]:
        """Send a customer reply, or replay the prior one."""
        return self._create(ticket_code, REPLY_KIND, payload.body, "ops-agent", idempotency_key)

    def _create(
        self, ticket_code: str, kind: str, body: str, author: str, idempotency_key: str
    ) -> tuple[NoteRead, bool]:
        prior = self._mutations.find_by_key(idempotency_key)
        if prior is not None:
            if prior.kind != kind:
                raise ConflictError(f"idempotency key already used for {prior.kind}")
            row = self._notes.get_by_id(TicketNote, prior.entity_id)
            if row is None:
                raise ConflictError("note log points to a missing row")
            return to_note_dto(row), False
        ticket = self._tickets.get_by_code(ticket_code)
        if ticket is None:
            raise NotFoundError(f"ticket {ticket_code} not found")
        note_kind = "internal" if kind == NOTE_KIND else "customer_reply"
        try:
            row = self._notes.create(
                ticket_id=ticket.id,
                kind=note_kind,
                body=body,
                author=author,
                mutation_key=idempotency_key,
            )
            self._mutations.record(idempotency_key, kind, row.id)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("duplicate note") from exc
        return to_note_dto(row), True


def to_note_dto(row: TicketNote) -> NoteRead:
    """Ticket-note mapping."""
    return NoteRead(
        id=row.id,
        ticket_id=row.ticket_id,
        kind=row.kind,
        body=row.body,
        author=row.author,
        mutation_key=row.mutation_key,
    )
