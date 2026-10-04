"""Control DTOs: chaos arming, reset, seed, oracle."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ArmFault(BaseModel):
    """Arm one fault: reproducible from type + target + trigger spec."""

    fault_type: str = Field(min_length=1, max_length=64)
    target: str = Field(min_length=1, max_length=200)
    trigger: dict[str, Any] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)


class FaultPlanRead(BaseModel):
    """Armed fault plan."""

    id: uuid.UUID
    fault_type: str
    target: str
    trigger: dict[str, Any]
    params: dict[str, Any]
    armed: bool


class ResetResult(BaseModel):
    """World reset acknowledgement with the (empty) world hash."""

    ok: bool = True
    world_hash: str


class SeedResult(BaseModel):
    """Seed acknowledgement with counts and the world hash."""

    counts: dict[str, int]
    world_hash: str


class OracleResult(BaseModel):
    """Independent expectation for one scenario (derived, never agent-made)."""

    scenario_id: str
    ticket_code: str
    expected_outcome: str
    expected_effects: list[dict[str, Any]]
    resolved_at: datetime
