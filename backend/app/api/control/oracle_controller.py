"""Control oracle controller: independent truth (operator token required)."""

from fastapi import APIRouter, Depends

from app.core.deps import require_operator
from app.schemas.control.control import OracleResult
from app.services.control.control_service import OracleService

router = APIRouter(tags=["control"])


@router.get("/api/control/oracle/{entity}", response_model=OracleResult)
def query_oracle(entity: str, _operator: None = Depends(require_operator)) -> OracleResult:
    """Oracle verdict for a scenario id (S1) or ticket code (TCK-101)."""
    return OracleService().query(entity)
