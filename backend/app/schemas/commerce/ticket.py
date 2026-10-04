"""Commerce read DTOs: tickets (body is untrusted customer text)."""

import uuid

from pydantic import BaseModel


class TicketRead(BaseModel):
    """Support ticket."""

    id: uuid.UUID
    code: str
    customer_id: uuid.UUID
    order_id: uuid.UUID | None
    subject: str
    body: str
    category: str
    status: str
    version: int
