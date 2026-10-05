"""Worker environment service: cookie-guarded operator proxy.

The browser never sees the operator token: these endpoints demand the
httponly ops-session cookie and call the control services in-process.
Fault arming, reset, and seed behave exactly like the control plane.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.schemas.control.control import ArmFault, FaultPlanRead, ResetResult, SeedResult
from app.schemas.worker.environment import EnvironmentStatus
from app.services.control.control_service import FaultService, ResetService, SeedService
from database.models.worker.flow import Approval, Clarification
from database.models.worker.task import Task


class EnvironmentService:
    """Stack status and control actions for the Control Center (`ns_app`)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def status(self) -> EnvironmentStatus:
        """Liveness plus queue depths (one row per queue, counted)."""
        try:
            self._session.query(func.count(Task.id)).scalar()
            database = "ok"
        except Exception:
            database = "error"
        return EnvironmentStatus(
            backend="ok",
            database=database,
            pending_tasks=self._count(Task, Task.status == "pending"),
            pending_approvals=self._count(Approval, Approval.status == "pending"),
            pending_clarifications=self._count(Clarification, Clarification.status == "pending"),
        )

    def arm_fault(self, payload: ArmFault) -> FaultPlanRead:
        """Arm one reproducible fault (same semantics as the control plane)."""
        return FaultService(self._session).arm(payload)

    @staticmethod
    def reset_world() -> ResetResult:
        """Truncate biz + worker (clears faults, seeds, and test rows)."""
        return ResetService().reset()

    @staticmethod
    def seed_world() -> SeedResult:
        """Load the deterministic seed world."""
        return SeedService().seed()

    def _count(self, model, condition) -> int:
        """Queue depth for one status condition."""
        return self._session.query(func.count(model.id)).filter(condition).scalar() or 0
