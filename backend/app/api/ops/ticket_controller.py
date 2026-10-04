"""Ops ticket controller: queue, detail, UI flags (session required)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_ops_session
from app.schemas.commerce.ticket import TicketRead
from app.schemas.ops.notes import UiFlags
from app.schemas.ops.tickets import TicketListResponse
from app.services.ops.ticket_service import FlagsService, OpsTicketService

router = APIRouter(tags=["ops-tickets"])


@router.get("/api/ops/tickets", response_model=TicketListResponse)
def list_tickets(
    page: int = 1,
    page_size: int = 10,
    session: Session = Depends(get_db),
    _agent: str = Depends(require_ops_session),
) -> TicketListResponse:
    """Paginated ticket queue."""
    return OpsTicketService(session).list_tickets(page, page_size)


@router.get("/api/ops/tickets/{ticket_code}", response_model=TicketRead)
def get_ticket(
    ticket_code: str,
    session: Session = Depends(get_db),
    _agent: str = Depends(require_ops_session),
) -> TicketRead:
    """Ticket detail."""
    return OpsTicketService(session).get_ticket(ticket_code)


@router.get("/api/ops/ui-flags", response_model=UiFlags)
def get_ui_flags(
    session: Session = Depends(get_db),
    _agent: str = Depends(require_ops_session),
) -> UiFlags:
    """UI behavior switches armed via fault plans."""
    return FlagsService(session).get_ui_flags()
