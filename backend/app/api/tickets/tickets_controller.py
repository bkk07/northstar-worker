"""Customer tickets controller (Phase 5).

Authenticated customers only: `POST /tickets` (raise), `GET /tickets`
(history), `GET /tickets/:id` (conversation), `POST /tickets/:id/messages`
(follow-up).
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.deps import get_db
from app.schemas.tickets import (
    TicketCreate,
    TicketDetail,
    TicketListItem,
    TicketMessageCreate,
    TicketMessageRead,
)
from app.services.tickets import ticket_service

router = APIRouter(tags=["tickets"])


@router.post("/tickets", response_model=TicketDetail, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    claims: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict:
    """Raise an OPEN ticket, optionally linked to one of your orders."""
    return ticket_service.create_ticket(
        session,
        user_id=str(claims["sub"]),
        subject=payload.subject,
        category=payload.category,
        description=payload.description,
        order_id=payload.order_id,
        priority=payload.priority,
    )


@router.get("/tickets", response_model=list[TicketListItem])
def list_tickets(
    claims: dict = Depends(get_current_user), session: Session = Depends(get_db)
) -> list[dict]:
    """Own tickets, newest first."""
    return ticket_service.list_tickets(session, user_id=str(claims["sub"]))


@router.get("/tickets/{ticket_id}", response_model=TicketDetail)
def get_ticket(
    ticket_id: str,
    claims: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict:
    """Ticket conversation with related-order context."""
    return ticket_service.get_ticket(
        session, user_id=str(claims["sub"]), ticket_id=ticket_id
    )


@router.post(
    "/tickets/{ticket_id}/messages",
    response_model=TicketMessageRead,
    status_code=status.HTTP_201_CREATED,
)
def add_message(
    ticket_id: str,
    payload: TicketMessageCreate,
    claims: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict:
    """Customer follow-up on an open ticket."""
    return ticket_service.add_message(
        session,
        user_id=str(claims["sub"]),
        ticket_id=ticket_id,
        message=payload.message,
    )
