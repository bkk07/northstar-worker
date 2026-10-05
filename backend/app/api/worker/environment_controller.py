"""Worker environment controller: cookie-guarded operator proxy.

The OPERATOR_TOKEN never reaches the browser: these routes demand the
httponly ops-session cookie (`require_ops_session`) and run the
control services in-process. Unauthenticated browsers get 401.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_ops_session
from app.schemas.control.control import ArmFault, FaultPlanRead, ResetResult, SeedResult
from app.schemas.worker.environment import EnvironmentStatus
from app.services.worker.environment_service import EnvironmentService

router = APIRouter(tags=["worker-environment"])


@router.get("/api/environment/status", response_model=EnvironmentStatus)
def environment_status(
    session: Session = Depends(get_db),
    _agent: str = Depends(require_ops_session),
) -> EnvironmentStatus:
    """Stack liveness plus queue depths for the dashboard cards."""
    return EnvironmentService(session).status()


@router.post(
    "/api/environment/faults", response_model=FaultPlanRead, status_code=status.HTTP_201_CREATED
)
def arm_environment_fault(
    payload: ArmFault,
    session: Session = Depends(get_db),
    _agent: str = Depends(require_ops_session),
) -> FaultPlanRead:
    """Arm one reproducible fault for the demo."""
    return EnvironmentService(session).arm_fault(payload)


@router.post("/api/environment/reset", response_model=ResetResult)
def reset_environment(
    _agent: str = Depends(require_ops_session),
) -> ResetResult:
    """Truncate biz + worker (clears faults, seeds, and test rows)."""
    return EnvironmentService.reset_world()


@router.post("/api/environment/seed", response_model=SeedResult)
def seed_environment(
    _agent: str = Depends(require_ops_session),
) -> SeedResult:
    """Load the deterministic seed world."""
    return EnvironmentService.seed_world()
