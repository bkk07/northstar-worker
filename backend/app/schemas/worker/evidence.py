"""Worker evidence schemas: terminal packets and screenshot index."""

import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class EvidencePacketRead(BaseModel):
    """Latest terminal packet for a task (summary is the 3-line brief)."""

    id: UUID
    task_id: UUID
    packet: dict[str, Any]
    summary: str
    created_at: datetime.datetime


class ScreenshotRead(BaseModel):
    """One indexed screenshot path for the run's evidence trail."""

    run_id: UUID
    label: str
    path: str
    created_at: datetime.datetime
