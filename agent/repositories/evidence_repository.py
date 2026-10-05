"""Evidence repository: packet and artifact rows (`worker.evidence`).

Packets are terminal-run records (one per run, latest wins for the
task); screenshots are artifact rows indexed per run. Both are
append-only proof — nothing here is ever updated.
"""

from collections.abc import Sequence
from uuid import UUID

from agent.repositories.base import BaseRepository
from database.models.worker.evidence import Evidence

PACKET_TYPE = "packet/v1"
SCREENSHOT_TYPE = "screenshot/v1"


class EvidenceRepository(BaseRepository[Evidence]):
    """`ns_runner`-role evidence writes, `ns_app` reads via the API."""

    def save_packet(self, task_id: UUID, packet: dict, summary: Sequence[str]) -> Evidence:
        """Persist one terminal packet (summary stored as joined lines)."""
        row = Evidence(
            task_id=task_id,
            packet={"type": PACKET_TYPE, **dict(packet)},
            summary="\n".join(summary),
        )
        self.add(row)
        self.flush()
        return self.refresh(row)

    def save_screenshot(self, task_id: UUID, run_id: UUID, label: str, path: str) -> Evidence:
        """Index one screenshot path for the run's evidence trail."""
        row = Evidence(
            task_id=task_id,
            packet={
                "type": SCREENSHOT_TYPE,
                "run_id": str(run_id),
                "label": label,
                "path": path,
            },
            summary=f"screenshot {label}: {path}",
        )
        self.add(row)
        self.flush()
        return self.refresh(row)

    def latest_packet(self, task_id: UUID) -> Evidence | None:
        """Newest terminal packet for the task (None before anything ends)."""
        return (
            self._session.query(Evidence)
            .filter(
                Evidence.task_id == task_id,
                Evidence.packet["type"].astext == PACKET_TYPE,
            )
            .order_by(Evidence.created_at.desc(), Evidence.id.desc())
            .first()
        )

    def screenshots_for_task(self, task_id: UUID) -> list[Evidence]:
        """Screenshot index for the task, oldest first."""
        return (
            self._session.query(Evidence)
            .filter(
                Evidence.task_id == task_id,
                Evidence.packet["type"].astext == SCREENSHOT_TYPE,
            )
            .order_by(Evidence.created_at.asc(), Evidence.id.asc())
            .all()
        )
