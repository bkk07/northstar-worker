"""Control services: fault arming, reset, seed, oracle (operator only)."""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.repositories.control.fault_plan_repository import FaultPlanRepository
from app.schemas.control.control import (
    ArmFault,
    FaultPlanRead,
    OracleResult,
    ResetResult,
    SeedResult,
)
from database.models.biz.ops import FaultPlan
from database.seeds import loader


class FaultService:
    """Arm chaos faults (services consume them exactly once)."""

    def __init__(self, session: Session) -> None:
        self._repos = FaultPlanRepository(session)
        self._session = session

    def arm(self, payload: ArmFault) -> FaultPlanRead:
        """Validate and persist an armed fault plan."""
        row = self._repos.arm(payload.fault_type, payload.target, payload.trigger, payload.params)
        self._session.commit()
        return self._to_dto(row)

    @staticmethod
    def _to_dto(row: FaultPlan) -> FaultPlanRead:
        return FaultPlanRead(
            id=row.id,
            fault_type=row.fault_type,
            target=row.target,
            trigger=row.trigger,
            params=row.params,
            armed=row.armed,
        )


class ResetService:
    """Truncate the world (also clears armed faults)."""

    def reset(self) -> ResetResult:
        """Reset biz + worker and return the empty-world hash."""
        loader.reset()
        return ResetResult(world_hash=loader.print_hash())


class SeedService:
    """Load the deterministic world."""

    def seed(self) -> SeedResult:
        """Seed and return counts with the world hash."""
        counts = loader.seed()
        return SeedResult(counts=counts, world_hash=loader.print_hash())


class OracleService:
    """Independent scenario truth over HTTP (eval harness + debugging)."""

    def query(self, entity: str) -> OracleResult:
        """Resolve a scenario id (S1) or ticket code (TCK-101) to its oracle."""
        from datetime import UTC, datetime

        import yaml

        from eval.oracle_rules import derive_expected, load_thresholds

        root = loader.SEED_DIR.parent.parent
        catalog = yaml.safe_load(
            (root / "eval" / "scenarios" / "catalog.yaml").read_text(encoding="utf-8")
        )
        policies = yaml.safe_load(
            (root / "database" / "seeds" / "policies.yaml").read_text(encoding="utf-8")
        )
        scenario = next(
            (s for s in catalog if s["id"] == entity or s["ticket_code"] == entity),
            None,
        )
        if scenario is None:
            held_out = yaml.safe_load(
                (root / "eval" / "held_out" / "catalog.yaml").read_text(encoding="utf-8")
            )
            scenario = next(
                (s for s in held_out if s["id"] == entity or s["ticket_code"] == entity),
                None,
            )
        if scenario is None:
            raise NotFoundError(f"no scenario for {entity!r}")
        verdict = derive_expected(
            scenario, scenario.get("intended_effects", []), load_thresholds(policies)
        )
        return OracleResult(
            scenario_id=scenario["id"],
            ticket_code=scenario["ticket_code"],
            expected_outcome=verdict.outcome,
            expected_effects=[dict(e) for e in verdict.effects],
            resolved_at=datetime.now(UTC),
        )
