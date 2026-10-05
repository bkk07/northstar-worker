"""Worker audit schemas: immutable history rows for the timeline."""

import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditEventRead(BaseModel):
    """One audit row in replay order (seq is gapless per DB)."""

    id: UUID
    task_id: UUID
    run_id: UUID | None
    seq: int
    ts: datetime.datetime
    node: str | None
    tool: str | None
    kind: str
    status: str | None
    error_type: str | None
    retry_count: int
    duration_ms: int | None
    policy_result: str | None
    verification_result: str | None
    payload: dict[str, Any]
