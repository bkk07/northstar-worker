"""Worker task DTOs: minimal create / read for the operator task queue."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    """Submit one operator task (explicit text or free-form)."""

    text: str = Field(min_length=1, max_length=2000)
    mode: str = Field(default="explicit", max_length=16)
    scenario_ref: str | None = Field(default=None, max_length=120)


class TaskRead(BaseModel):
    """One task row (lifecycle owned by the runner)."""

    id: uuid.UUID
    text: str
    mode: str
    status: str
    current_state: str
    scenario_ref: str | None
    created_by: str
    created_at: datetime
