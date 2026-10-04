"""Armed fault-plan reads (UI switches for `/ops`)."""

from app.repositories.base import BaseRepository
from database.models.biz.ops import FaultPlan


class FaultRepository(BaseRepository[FaultPlan]):
    """Read access to `biz.fault_plans` (control plane owns writes)."""

    def list_armed(self) -> list[FaultPlan]:
        """Fault plans that are armed and not yet consumed."""
        return (
            self._session.query(FaultPlan)
            .filter(FaultPlan.armed.is_(True), FaultPlan.consumed_at.is_(None))
            .all()
        )
