"""Shop service: customer order views and raise-ticket form."""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.repositories.commerce.customer_repository import CustomerRepository
from app.repositories.commerce.order_repository import OrderRepository
from app.repositories.ops.ticket_repository import TicketRepository
from app.schemas.commerce.order import OrderRead
from app.schemas.commerce.ticket import TicketRead
from app.schemas.shop.shop import ShopTicketCreate
from app.services.commerce.order_service import OrderService
from app.services.commerce.ticket_service import to_ticket_dto
from database.models.biz.ticket import Ticket


class ShopService:
    """Customer surface (no session required)."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._orders = OrderService(session)
        self._customers = CustomerRepository(session)
        self._order_repos = OrderRepository(session)
        self._tickets = TicketRepository(session)

    def list_orders(self, customer_code: str | None = None) -> list[OrderRead]:
        """Orders, optionally filtered to one customer."""
        if customer_code is None:
            return []
        customer = self._customers.get_by_code(customer_code)
        if customer is None:
            raise NotFoundError(f"customer {customer_code} not found")
        return self._orders.list_by_customer(customer.id)

    def get_order(self, order_code: str) -> OrderRead:
        """Order detail or 404."""
        return self._orders.get_by_code(order_code)

    def list_order_tickets(self, order_code: str) -> list[TicketRead]:
        """Tickets raised against one order, newest first (or 404)."""
        order = self._order_repos.get_by_code(order_code)
        if order is None:
            raise NotFoundError(f"order {order_code} not found")
        rows = (
            self._session.query(Ticket)
            .filter(Ticket.order_id == order.id)
            .order_by(Ticket.created_at.desc())
            .all()
        )
        return [to_ticket_dto(ticket) for ticket in rows]

    def create_ticket(self, payload: ShopTicketCreate) -> TicketRead:
        """Raise a ticket from the shop (open status, generated code)."""
        customer = self._customers.get_by_code(payload.customer_code)
        if customer is None:
            raise NotFoundError(f"customer {payload.customer_code} not found")
        order_id = None
        if payload.order_code is not None:
            order = self._order_repos.get_by_code(payload.order_code)
            if order is None:
                raise NotFoundError(f"order {payload.order_code} not found")
            order_id = order.id
        code = f"TCK-{uuid.uuid4().hex[:8].upper()}"
        ticket = self._tickets.create(
            code=code,
            customer_id=customer.id,
            order_id=order_id,
            subject=payload.subject,
            body=payload.body,
            category=payload.category,
        )
        self._session.commit()
        return to_ticket_dto(ticket)

    def get_ticket(self, ticket_code: str) -> TicketRead:
        """Ticket status for the customer or 404."""
        ticket = self._tickets.get_by_code(ticket_code)
        if ticket is None:
            raise NotFoundError(f"ticket {ticket_code} not found")
        return to_ticket_dto(ticket)
