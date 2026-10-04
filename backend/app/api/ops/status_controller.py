"""Ops status controller: ticket status changes (idempotent)."""

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_ops_session
from app.schemas.commerce.ticket import TicketRead
from app.schemas.ops.notes import StatusUpdate
from app.services.ops.status_service import StatusService

router = APIRouter(tags=["ops-status"])


@router.post("/api/ops/tickets/{ticket_code}/status", response_model=TicketRead)
def update_status(
    ticket_code: str,
    payload: StatusUpdate,
    response: Response,
    session: Session = Depends(get_db),
    _agent: str = Depends(require_ops_session),
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> TicketRead:
    """Change ticket status (201) or replay it (200)."""
    dto, created = StatusService(session).update(ticket_code, payload, idempotency_key)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return dto
