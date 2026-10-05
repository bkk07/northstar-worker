"""Worker clarification DTOs: operator and customer question queues."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ClarificationAnswer(BaseModel):
    """Answer a pending clarification (requeues the parked task)."""

    answer: str = Field(min_length=1, max_length=2000)
    answered_by: str = Field(min_length=1, max_length=120)


class ClarificationRead(BaseModel):
    """One clarification request with its kind, question, and answer."""

    id: uuid.UUID
    task_id: uuid.UUID
    kind: str
    question: str
    answer: str | None
    answered_by: str | None
    status: str
    created_at: datetime
