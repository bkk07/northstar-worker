"""Ops reply controller: customer-visible replies (idempotent)."""

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_ops_session
from app.schemas.ops.notes import NoteRead, ReplyCreate
from app.services.ops.note_service import NoteService

router = APIRouter(tags=["ops-replies"])


@router.post("/api/ops/tickets/{ticket_code}/reply", response_model=NoteRead)
def create_reply(
    ticket_code: str,
    payload: ReplyCreate,
    response: Response,
    session: Session = Depends(get_db),
    _agent: str = Depends(require_ops_session),
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> NoteRead:
    """Send a customer reply (201) or replay it (200)."""
    dto, created = NoteService(session).create_reply(ticket_code, payload, idempotency_key)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return dto
