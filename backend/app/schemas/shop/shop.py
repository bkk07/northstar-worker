"""Shop DTOs: customer ticket creation (no session, no idempotency key)."""

from pydantic import BaseModel, Field


class ShopTicketCreate(BaseModel):
    """Raise-ticket form: customer-identified, optionally order-linked."""

    customer_code: str = Field(min_length=1)
    order_code: str | None = None
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)
    category: str = Field(default="general", max_length=64)
