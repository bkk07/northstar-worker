"""Agent direct-commit DTOs: service-layer writes without the browser."""

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


class DirectCommitRequest(BaseModel):
    """One token-authorized commit (params mirror the submit action)."""

    task_id: str = Field(min_length=1)
    effect: Literal["refund.create", "replacement.create"]
    mutation_key: str = Field(min_length=1, max_length=64)
    token: str = Field(min_length=1)
    params: dict[str, Any] = Field(description="Effect params incl. 'effect'")


class DirectCommitReply(BaseModel):
    """Commit outcome (replays report created=false, same entity)."""

    ok: bool = True
    effect: str
    created: bool
    entity_id: uuid.UUID
    mutation_key: str
    status: int
