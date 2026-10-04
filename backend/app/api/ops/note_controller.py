"""Ops note controller: internal notes (idempotent)."""

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_ops_session
from app.schemas.ops.notes import NoteCreate, NoteRead
from app.services.ops.note_service import NoteService

router = APIRouter(tags=["ops-notes"])


@router.post("/api/ops/tickets/{ticket_code}/notes", response_model=NoteRead)
def create_note(
    ticket_code: str,
    payload: NoteCreate,
    response: Response,
    session: Session = Depends(get_db),
    _agent: str = Depends(require_ops_session),
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> NoteRead:
    """Attach an internal note (201) or replay it (200)."""
    dto, created = NoteService(session).create_note(ticket_code, payload, idempotency_key)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return dto
