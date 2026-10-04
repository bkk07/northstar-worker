"""Commerce read DTOs: refunds and replacements."""

import uuid

from pydantic import BaseModel


class RefundRead(BaseModel):
    """Refund row."""

    id: uuid.UUID
    order_id: uuid.UUID
    customer_id: uuid.UUID
    ticket_id: uuid.UUID
    amount_paise: int
    status: str
    mutation_key: str


class ReplacementRead(BaseModel):
    """Replacement row."""

    id: uuid.UUID
    order_id: uuid.UUID
    order_item_id: uuid.UUID
    customer_id: uuid.UUID
    ticket_id: uuid.UUID
    status: str
    mutation_key: str
