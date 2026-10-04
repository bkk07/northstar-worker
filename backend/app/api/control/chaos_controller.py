"""Control chaos controller: arm faults (operator token required)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_operator
from app.schemas.control.control import ArmFault, FaultPlanRead
from app.services.control.control_service import FaultService

router = APIRouter(tags=["control"])


@router.post(
    "/api/control/chaos", response_model=FaultPlanRead, status_code=status.HTTP_201_CREATED
)
def arm_fault(
    payload: ArmFault,
    session: Session = Depends(get_db),
    _operator: None = Depends(require_operator),
) -> FaultPlanRead:
    """Arm one reproducible fault."""
    return FaultService(session).arm(payload)
