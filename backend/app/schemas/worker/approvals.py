"""Worker approval DTOs: operator decision queue for held commits."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ApprovalDecide(BaseModel):
    """Approve or reject a pending approval (single-use, bound, expiring)."""

    approver: str = Field(min_length=1, max_length=120)


class ApprovalRead(BaseModel):
    """One approval request with the action, params, reason, and rule."""

    id: uuid.UUID
    task_id: uuid.UUID
    requested_action: str
    params: dict
    params_hash: str
    reason: str
    policy_rule_id: str
    status: str
    approver: str | None
    resolved_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
