"""Worker environment schemas: stack status for the dashboard cards."""

from pydantic import BaseModel


class EnvironmentStatus(BaseModel):
    """Liveness plus queue depths (drives the dashboard cards)."""

    backend: str
    database: str
    pending_tasks: int
    pending_approvals: int
    pending_clarifications: int
