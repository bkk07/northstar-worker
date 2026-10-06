"""Phase 5 customer-ticket DTOs: raise ticket, history, conversation (spec §9)."""

from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    """Raise a ticket: subject, category, description, related order."""

    subject: str = Field(min_length=5, max_length=200)
    category: str = Field(min_length=1)
    description: str = Field(min_length=10, max_length=2000)
    order_id: str | None = None
    priority: str = Field(default="NORMAL")


class TicketMessageCreate(BaseModel):
    """Customer follow-up on an open ticket."""

    message: str = Field(min_length=1, max_length=2000)


class TicketMessageRead(BaseModel):
    """One conversation message."""

    id: str
    sender_type: str
    message: str
    created_at: str


class RelatedOrderRead(BaseModel):
    """Order context linked to a ticket."""

    id: str
    order_number: str
    status: str
    total_display: str
    item_count: int


class TicketListItem(BaseModel):
    """Ticket history row (`GET /tickets`)."""

    id: str
    ticket_number: str
    subject: str
    category: str
    priority: str
    status: str
    order_number: str | None = None
    message_count: int
    created_at: str


class TicketDetail(BaseModel):
    """Ticket conversation page (`GET /tickets/:id`)."""

    id: str
    ticket_number: str
    subject: str
    description: str
    category: str
    priority: str
    status: str
    resolution: str | None = None
    created_at: str
    related_order: RelatedOrderRead | None = None
    messages: list[TicketMessageRead]
