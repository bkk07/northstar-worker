"""Evaluation service: recorded runs plus the scenario catalog."""

from uuid import UUID

import yaml
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.schemas.evaluation.evaluation import (
    EvalResultRead,
    EvalRunCreate,
    EvalRunDetail,
    EvalRunRead,
    EvalScenarioRead,
)
from database.models.worker.evaluation import EvalResult, EvalRun
from database.seeds import loader


class EvaluationService:
    """Eval ledger over `worker.eval_runs` / `worker.eval_results` (`ns_app`)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record_run(self, payload: EvalRunCreate) -> EvalRunRead:
        """Store one suite run with its per-scenario scores."""
        run = EvalRun(
            suite=payload.suite,
            scenario_count=payload.scenario_count,
            metrics=dict(payload.metrics),
            report_md=payload.report_md,
        )
        self._session.add(run)
        self._session.flush()
        for result in payload.results:
            self._session.add(
                EvalResult(
                    run_id=run.id,
                    scenario_id=result.scenario_id,
                    expected_outcome=result.expected_outcome,
                    actual_outcome=result.actual_outcome,
                    outcome_ok=result.outcome_ok,
                    scores=dict(result.scores),
                )
            )
        self._session.commit()
        self._session.refresh(run)
        return self._to_run_dto(run)

    def list_runs(self, limit: int = 20) -> list[EvalRunRead]:
        """Newest runs first (metrics ledgers for the comparison UI)."""
        rows = (
            self._session.query(EvalRun)
            .order_by(EvalRun.created_at.desc(), EvalRun.id.desc())
            .limit(max(limit, 1))
            .all()
        )
        return [self._to_run_dto(row) for row in rows]

    def get_run(self, run_id: UUID) -> EvalRunDetail:
        """One run with its per-scenario drilldown rows (404 when absent)."""
        run = self._session.get(EvalRun, run_id)
        if run is None:
            raise NotFoundError(f"eval run {run_id} not found")
        rows = (
            self._session.query(EvalResult)
            .filter(EvalResult.run_id == run_id)
            .order_by(EvalResult.scenario_id.asc())
            .all()
        )
        return EvalRunDetail(
            run=self._to_run_dto(run),
            results=[
                EvalResultRead(
                    id=row.id,
                    scenario_id=row.scenario_id,
                    expected_outcome=row.expected_outcome,
                    actual_outcome=row.actual_outcome,
                    outcome_ok=row.outcome_ok,
                    scores=dict(row.scores or {}),
                    created_at=row.created_at,
                )
                for row in rows
            ],
        )

    def list_scenarios(self, suite: str = "seeded") -> list[EvalScenarioRead]:
        """Catalog rows for a suite (seeded or held_out; same oracle source)."""
        root = loader.SEED_DIR.parent.parent / "eval"
        catalog_file = (
            root / "held_out" / "catalog.yaml"
            if suite == "held_out"
            else root / "scenarios" / "catalog.yaml"
        )
        catalog = yaml.safe_load(catalog_file.read_text(encoding="utf-8"))
        return [
            EvalScenarioRead(
                id=row["id"],
                category=row.get("category", ""),
                mode=row.get("mode", ""),
                ticket_code=row.get("ticket_code", ""),
                task=row.get("task", ""),
                expected_outcome=row.get("expected_outcome", ""),
                expected_effects=[dict(e) for e in row.get("expected_effects", [])],
            )
            for row in catalog
        ]

    @staticmethod
    def _to_run_dto(row: EvalRun) -> EvalRunRead:
        return EvalRunRead(
            id=row.id,
            suite=row.suite,
            scenario_count=row.scenario_count,
            metrics=dict(row.metrics or {}),
            report_md=row.report_md,
            created_at=row.created_at,
        )
