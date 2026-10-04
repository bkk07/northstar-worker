"""Fault-plan writes (control plane arms, services consume)."""

from app.faults.registry import validate_plan
from app.repositories.base import BaseRepository
from database.models.biz.ops import FaultPlan


class FaultPlanRepository(BaseRepository[FaultPlan]):
    """Persistence for `biz.fault_plans`."""

    def arm(self, fault_type: str, target: str, trigger: dict, params: dict) -> FaultPlan:
        """Validate and insert an armed fault plan (caller commits)."""
        validate_plan(fault_type, target, trigger)
        row = FaultPlan(
            fault_type=fault_type,
            target=target,
            trigger=trigger,
            params=params,
            armed=True,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def list_armed(self) -> list[FaultPlan]:
        """Plans that are armed and not yet consumed."""
        return (
            self._session.query(FaultPlan)
            .filter(FaultPlan.armed.is_(True), FaultPlan.consumed_at.is_(None))
            .all()
        )
