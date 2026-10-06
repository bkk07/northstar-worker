"""Phase 6 support-console DTOs: dashboard, queue, context, manual actions."""

from pydantic import BaseModel, Field


class DashboardStats(BaseModel):
    """Ticket counts by status + summary cards."""

    by_status: dict[str, int]
    summary: dict[str, int]


class QueueTicket(BaseModel):
    """One ticket-queue row."""

    id: str
    ticket_number: str
    subject: str
    category: str
    priority: str
    status: str
    customer_name: str
    customer_email: str
    order_number: str | None = None
    message_count: int
    created_at: str


class SupportMessage(BaseModel):
    """Conversation message (internal notes visible to staff only)."""

    id: str
    sender_type: str
    message: str
    is_internal: bool
    created_at: str


class CustomerProfile(BaseModel):
    """Customer context."""

    id: str
    name: str
    email: str
    created_at: str | None = None


class OrderLine(BaseModel):
    """Related-order line."""

    product_name: str
    quantity: int
    unit_price_paise: int
    line_total_paise: int


class RelatedOrderFull(BaseModel):
    """Complete related-order context."""

    id: str
    order_number: str
    status: str
    total_display: str
    payment_status: str
    payment_reference: str | None = None
    shipping_address: str
    ordered_at: str
    items: list[OrderLine]


class PolicyRef(BaseModel):
    """Per-product policy summary for the related order."""

    product_name: str
    summary: str
    return_allowed: bool
    refund_allowed: bool
    cancellation_allowed: bool


class OrderRef(BaseModel):
    """Recent-order row."""

    id: str
    order_number: str
    status: str
    total_display: str
    ordered_at: str


class TicketRef(BaseModel):
    """Previous-ticket row."""

    id: str
    ticket_number: str
    subject: str
    status: str


class SupportTicketDetail(BaseModel):
    """Full console context for one ticket."""

    id: str
    ticket_number: str
    subject: str
    description: str
    category: str
    priority: str
    status: str
    resolution: str | None = None
    created_at: str
    customer: CustomerProfile
    related_order: RelatedOrderFull | None = None
    policies: list[PolicyRef]
    recent_orders: list[OrderRef]
    previous_tickets: list[TicketRef]
    messages: list[SupportMessage]


class ReplyCreate(BaseModel):
    """Manual customer-visible reply."""

    message: str = Field(min_length=1, max_length=2000)


class NoteCreate(BaseModel):
    """Internal note (never shown to the customer)."""

    message: str = Field(min_length=1, max_length=2000)


class ResolveCreate(BaseModel):
    """Resolve with a resolution note."""

    resolution: str = Field(min_length=5, max_length=2000)


class EscalateCreate(BaseModel):
    """Escalate with an optional reason."""

    reason: str | None = Field(default=None, max_length=500)


class StatusUpdate(BaseModel):
    """Result of resolve / escalate."""

    id: str
    status: str
    resolution: str | None = None
