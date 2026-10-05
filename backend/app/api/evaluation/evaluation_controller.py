"""Evaluation controller: recorded runs and the scenario catalog."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.evaluation.evaluation import (
    EvalRunCreate,
    EvalRunDetail,
    EvalRunRead,
    EvalScenarioRead,
)
from app.services.evaluation.evaluation_service import EvaluationService

router = APIRouter(tags=["evaluation"])


@router.post("/api/eval/runs", response_model=EvalRunRead, status_code=status.HTTP_201_CREATED)
def record_run(payload: EvalRunCreate, session: Session = Depends(get_db)) -> EvalRunRead:
    """Record one suite run with its metrics and per-scenario scores."""
    return EvaluationService(session).record_run(payload)


@router.get("/api/eval/runs", response_model=list[EvalRunRead])
def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_db),
) -> list[EvalRunRead]:
    """Newest runs first (metrics ledgers for the comparison UI)."""
    return EvaluationService(session).list_runs(limit=limit)


@router.get("/api/eval/runs/{run_id}", response_model=EvalRunDetail)
def get_run(run_id: UUID, session: Session = Depends(get_db)) -> EvalRunDetail:
    """One run with its per-scenario drilldown rows."""
    return EvaluationService(session).get_run(run_id)


@router.get("/api/eval/scenarios", response_model=list[EvalScenarioRead])
def list_scenarios(session: Session = Depends(get_db)) -> list[EvalScenarioRead]:
    """Seeded catalog rows (the same file the oracle derives from)."""
    return EvaluationService(session).list_scenarios()
