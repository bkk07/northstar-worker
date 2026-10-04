"""Ops ticket queue service + UI flags service."""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.repositories.commerce.customer_repository import CustomerRepository
from app.repositories.ops.fault_repository import FaultRepository
from app.repositories.ops.ticket_repository import TicketRepository
from app.schemas.commerce.customer import CustomerRead
from app.schemas.commerce.ticket import TicketRead
from app.schemas.ops.notes import UiFlags
from app.schemas.ops.tickets import TicketListResponse
from app.services.commerce.ticket_service import to_ticket_dto

UI_FLAG_BY_FAULT = {
    "REMOVED_SEARCH_FIELD": "removed_search_field",
    "DOM_DRIFT": "dom_drift",
    "STALE_ELEMENT": "stale_rerender",
}


class OpsTicketService:
    """Ticket queue, detail, and customer search for `/ops`."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._tickets = TicketRepository(session)
        self._customers = CustomerRepository(session)

    def list_tickets(self, page: int, page_size: int) -> TicketListResponse:
        """Paginated queue (10 per page)."""
        page = max(page, 1)
        page_size = min(max(page_size, 1), 50)
        items, total = self._tickets.list_paginated(page, page_size)
        return TicketListResponse(
            items=[to_ticket_dto(t) for t in items],
            page=page,
            page_size=page_size,
            total=total,
        )

    def get_ticket(self, ticket_code: str) -> TicketRead:
        """Ticket detail or 404."""
        ticket = self._tickets.get_by_code(ticket_code)
        if ticket is None:
            raise NotFoundError(f"ticket {ticket_code} not found")
        return to_ticket_dto(ticket)

    def search_customers(self, query: str) -> list[CustomerRead]:
        """Customer search with look-alikes."""
        return [
            CustomerRead(id=c.id, code=c.code, name=c.name, email=c.email)
            for c in self._customers.search(query)
        ]


class FlagsService:
    """UI switches derived from armed fault plans (Phase 9 arms them)."""

    def __init__(self, session: Session) -> None:
        self._faults = FaultRepository(session)

    def get_ui_flags(self) -> UiFlags:
        """Flags on when a matching fault plan is armed."""
        flags = UiFlags()
        for plan in self._faults.list_armed():
            attr = UI_FLAG_BY_FAULT.get(plan.fault_type)
            if attr is not None:
                setattr(flags, attr, True)
        return flags
