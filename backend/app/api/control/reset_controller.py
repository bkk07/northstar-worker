"""Control reset/seed controllers (operator token required)."""

from fastapi import APIRouter, Depends

from app.core.deps import require_operator
from app.schemas.control.control import ResetResult, SeedResult
from app.services.control.control_service import ResetService, SeedService

router = APIRouter(tags=["control"])


@router.post("/api/control/reset", response_model=ResetResult)
def reset_world(_operator: None = Depends(require_operator)) -> ResetResult:
    """Truncate biz + worker (clears faults, seeds, and test rows)."""
    return ResetService().reset()


@router.post("/api/control/seed", response_model=SeedResult)
def seed_world(_operator: None = Depends(require_operator)) -> SeedResult:
    """Load the deterministic seed world."""
    return SeedService().seed()
