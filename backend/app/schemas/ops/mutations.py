"""Ops DTOs: replacement and refund mutation requests."""

from pydantic import BaseModel, Field, PositiveInt


class ReplacementCreate(BaseModel):
    """Replacement request, addressed by human codes (UI-friendly)."""

    order_code: str = Field(min_length=1)
    item_sku: str = Field(min_length=1)
    ticket_code: str = Field(min_length=1)
    reason: str | None = None


class RefundCreate(BaseModel):
    """Refund request in integer paise."""

    order_code: str = Field(min_length=1)
    ticket_code: str = Field(min_length=1)
    amount_paise: PositiveInt
