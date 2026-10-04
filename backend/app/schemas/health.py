"""Health DTO (Pydantic v2). Crosses controller/service layers."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "northstar-worker-backend"
    version: str = "0.1.0-phase1"
