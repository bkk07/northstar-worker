"""Commerce read DTOs: mutation probe."""

import uuid

from pydantic import BaseModel


class ProbeResult(BaseModel):
    """Mutation probe: found + identity when present, never an error."""

    found: bool
    kind: str | None = None
    entity_id: uuid.UUID | None = None
