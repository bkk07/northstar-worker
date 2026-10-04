"""Health service: business logic behind the health check.

Layering: services may import schemas + common only (never controllers).
"""

from app.schemas.health import HealthResponse


def get_health() -> HealthResponse:
    """Return service liveness (DB checks arrive in Phase 4)."""
    return HealthResponse(status="ok")
