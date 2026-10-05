"""Worker evidence service: terminal packets and screenshot index.

The packet is the proof presentation — summary, effects, policy,
verification, recovery, memory provenance, screenshots, and the audit
pointer — built by `FinalizationService` and persisted by the runner.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.schemas.worker.evidence import EvidencePacketRead, ScreenshotRead
from database.models.worker.evidence import Evidence
from database.models.worker.task import Task

PACKET_TYPE = "packet/v1"
SCREENSHOT_TYPE = "screenshot/v1"


class EvidenceService:
    """Read-only evidence over `worker.evidence` (`ns_app` role)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def latest_packet(self, task_id: UUID) -> EvidencePacketRead:
        """Newest terminal packet (404 when the task never ended)."""
        if self._session.get(Task, task_id) is None:
            raise NotFoundError(f"task {task_id} not found")
        row = (
            self._session.query(Evidence)
            .filter(
                Evidence.task_id == task_id,
                Evidence.packet["type"].astext == PACKET_TYPE,
            )
            .order_by(Evidence.created_at.desc(), Evidence.id.desc())
            .first()
        )
        if row is None:
            raise NotFoundError(f"no evidence packet for task {task_id}")
        return EvidencePacketRead(
            id=row.id,
            task_id=row.task_id,
            packet=dict(row.packet or {}),
            summary=row.summary,
            created_at=row.created_at,
        )

    def screenshots_for_task(self, task_id: UUID) -> list[ScreenshotRead]:
        """Screenshot index for the task, oldest first."""
        if self._session.get(Task, task_id) is None:
            raise NotFoundError(f"task {task_id} not found")
        rows = (
            self._session.query(Evidence)
            .filter(
                Evidence.task_id == task_id,
                Evidence.packet["type"].astext == SCREENSHOT_TYPE,
            )
            .order_by(Evidence.created_at.asc(), Evidence.id.asc())
            .all()
        )
        return [
            ScreenshotRead(
                run_id=UUID(
                    (row.packet or {}).get("run_id", "00000000-0000-0000-0000-000000000000")
                ),
                label=str((row.packet or {}).get("label", "")),
                path=str((row.packet or {}).get("path", "")),
                created_at=row.created_at,
            )
            for row in rows
        ]
