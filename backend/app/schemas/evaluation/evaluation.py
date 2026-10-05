"""Evaluation DTOs: recorded runs, scenario scores, catalog rows."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EvalResultCreate(BaseModel):
    """One scored scenario inside a run."""

    scenario_id: str = Field(max_length=16)
    expected_outcome: str = Field(max_length=32)
    actual_outcome: str = Field(max_length=32)
    outcome_ok: bool = False
    scores: dict[str, Any] = Field(default_factory=dict)


class EvalRunCreate(BaseModel):
    """Record a suite run with its metrics and per-scenario scores."""

    suite: str = Field(min_length=1, max_length=64)
    scenario_count: int = Field(default=0, ge=0)
    metrics: dict[str, Any] = Field(default_factory=dict)
    results: list[EvalResultCreate] = Field(default_factory=list)
    report_md: str = ""


class EvalResultRead(BaseModel):
    """One stored scenario score."""

    id: uuid.UUID
    scenario_id: str
    expected_outcome: str
    actual_outcome: str
    outcome_ok: bool
    scores: dict[str, Any]
    created_at: datetime


class EvalRunRead(BaseModel):
    """One stored suite run (metrics ledger for the table)."""

    id: uuid.UUID
    suite: str
    scenario_count: int
    metrics: dict[str, Any]
    report_md: str
    created_at: datetime


class EvalRunDetail(BaseModel):
    """A run with its per-scenario drilldown rows."""

    run: EvalRunRead
    results: list[EvalResultRead]


class EvalScenarioRead(BaseModel):
    """One catalog scenario (outcome + effects; facts stay server-side)."""

    id: str
    category: str
    mode: str
    ticket_code: str
    task: str
    expected_outcome: str
    expected_effects: list[dict[str, Any]]
