"""Worker memory DTOs: sourced working-memory items with trust."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class MemoryItemRead(BaseModel):
    """One memory fact with provenance, timestamp, and run."""

    id: uuid.UUID
    run_id: uuid.UUID
    key: str
    value: dict
    source_type: str
    source_ref: str | None
    trust: str
    confidence: float | None
    created_at: datetime
