"""Support console controller (Phase 6, `SUPPORT_AGENT` only).

Dashboard stats, ticket queue with filters, full ticket context, and manual
actions (reply, internal note, resolve, escalate). AI solve arrives Phase 8+.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.deps import get_db
from app.schemas.support import (
    DashboardStats,
    EscalateCreate,
    NoteCreate,
    QueueTicket,
    ReplyCreate,
    ResolveCreate,
    StatusUpdate,
    SupportMessage,
    SupportTicketDetail,
)
from app.services.support import support_service

router = APIRouter(tags=["support"])

_staff = require_roles("SUPPORT_AGENT")


@router.get("/support/stats", response_model=DashboardStats)
def dashboard_stats(
    claims: dict = Depends(_staff), session: Session = Depends(get_db)
) -> dict:
    """Ticket counts by status + summary cards."""
    return support_service.dashboard_stats(session)


@router.get("/support/tickets", response_model=list[QueueTicket])
def list_queue(
    status: str | None = None,
    priority: str | None = None,
    q: str | None = None,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> list[dict]:
    """Ticket queue with status/priority/search filters."""
    return support_service.list_queue(session, status=status, priority=priority, search=q)


@router.get("/support/tickets/{ticket_id}", response_model=SupportTicketDetail)
def get_ticket_detail(
    ticket_id: str,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> dict:
    """Full console context for one ticket."""
    return support_service.get_ticket_detail(session, ticket_id=ticket_id)


@router.post("/support/tickets/{ticket_id}/reply", response_model=SupportMessage)
def reply(
    ticket_id: str,
    payload: ReplyCreate,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> dict:
    """Manual customer-visible reply."""
    return support_service.reply(
        session, staff_id=str(claims["sub"]), ticket_id=ticket_id, message=payload.message
    )


@router.post("/support/tickets/{ticket_id}/notes", response_model=SupportMessage)
def add_note(
    ticket_id: str,
    payload: NoteCreate,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> dict:
    """Internal note (never shown to the customer)."""
    return support_service.add_note(
        session, staff_id=str(claims["sub"]), ticket_id=ticket_id, message=payload.message
    )


@router.post("/support/tickets/{ticket_id}/resolve", response_model=StatusUpdate)
def resolve(
    ticket_id: str,
    payload: ResolveCreate,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> dict:
    """Resolve with a resolution note."""
    return support_service.resolve(
        session,
        staff_id=str(claims["sub"]),
        ticket_id=ticket_id,
        resolution=payload.resolution,
    )


@router.post("/support/tickets/{ticket_id}/escalate", response_model=StatusUpdate)
def escalate(
    ticket_id: str,
    payload: EscalateCreate,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> dict:
    """Escalate an actionable ticket."""
    return support_service.escalate(
        session, staff_id=str(claims["sub"]), ticket_id=ticket_id, reason=payload.reason
    )
