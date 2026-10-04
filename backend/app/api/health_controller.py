"""Health controller (HTTP only): GET /api/health.

Layering: controllers import services + schemas only (never repositories).
"""

from fastapi import APIRouter

from app.schemas.health import HealthResponse
from app.services import health_service

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Liveness probe used by Phase 1 manual verification."""
    return health_service.get_health()
