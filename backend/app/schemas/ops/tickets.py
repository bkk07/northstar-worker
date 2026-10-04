"""Ops DTOs: ticket queue (10 per page) and detail."""

from pydantic import BaseModel

from app.schemas.commerce.ticket import TicketRead


class TicketListResponse(BaseModel):
    """Paginated ticket queue (the worker must paginate)."""

    items: list[TicketRead]
    page: int
    page_size: int
    total: int
