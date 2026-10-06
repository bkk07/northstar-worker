"""Shop controller: customer order views and raise-ticket form."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.commerce.order import OrderRead
from app.schemas.commerce.ticket import TicketRead
from app.schemas.shop.shop import ShopTicketCreate
from app.services.commerce.shop_service import ShopService

router = APIRouter(tags=["shop"])


@router.get("/api/shop/orders", response_model=list[OrderRead])
def list_orders(
    customer_code: str | None = None, session: Session = Depends(get_db)
) -> list[OrderRead]:
    """Customer orders, optionally filtered by customer code."""
    return ShopService(session).list_orders(customer_code)


@router.get("/api/shop/orders/{order_code}", response_model=OrderRead)
def get_order(order_code: str, session: Session = Depends(get_db)) -> OrderRead:
    """Order detail."""
    return ShopService(session).get_order(order_code)


@router.get("/api/shop/orders/{order_code}/tickets", response_model=list[TicketRead])
def list_order_tickets(order_code: str, session: Session = Depends(get_db)) -> list[TicketRead]:
    """Tickets raised against one order, newest first."""
    return ShopService(session).list_order_tickets(order_code)


@router.post("/api/shop/tickets", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: ShopTicketCreate, session: Session = Depends(get_db)) -> TicketRead:
    """Raise a ticket from the shop."""
    return ShopService(session).create_ticket(payload)


@router.get("/api/shop/tickets/{ticket_code}", response_model=TicketRead)
def get_ticket(ticket_code: str, session: Session = Depends(get_db)) -> TicketRead:
    """Ticket status for the customer."""
    return ShopService(session).get_ticket(ticket_code)
