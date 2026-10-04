"""Commerce read DTOs: orders and items (money in paise)."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class OrderItemRead(BaseModel):
    """One order line."""

    id: uuid.UUID
    sku: str
    title: str
    qty: int
    unit_paise: int
    category: str


class OrderRead(BaseModel):
    """Order with its items."""

    id: uuid.UUID
    code: str
    customer_id: uuid.UUID
    status: str
    total_paise: int
    paid_paise: int
    placed_at: datetime
    delivered_at: datetime | None
    items: list[OrderItemRead] = []
