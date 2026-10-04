"""Commerce read DTOs: customers."""

import uuid

from pydantic import BaseModel


class CustomerRead(BaseModel):
    """Customer as seen by read APIs and the shop."""

    id: uuid.UUID
    code: str
    name: str
    email: str
