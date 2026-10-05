"""Worker verification schemas: independent proof per run."""

import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class VerificationRead(BaseModel):
    """One persisted verifier verdict for a task run."""

    id: UUID
    run_id: UUID
    verdict: str
    invariants: dict[str, Any]
    diff: dict[str, Any]
    computed_at: datetime.datetime
