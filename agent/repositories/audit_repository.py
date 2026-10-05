"""Audit repository: append-only events (`worker.audit_events`).

Every node transition, tool call, policy decision, failure, recovery,
approval, and verification result lands here. UPDATE/DELETE are revoked
for all worker roles (Phase 4 grants); history is never rewritten.
Reads are seq-ordered so any run's chain replays exactly.
"""

from uuid import UUID

from agent.repositories.base import BaseRepository
from database.models.worker.audit import AuditEvent


class AuditRepository(BaseRepository[AuditEvent]):
    """`ns_runner`-role audit appends (runner + audit emitter)."""

    def append(
        self,
        task_id: UUID,
        run_id: UUID | None,
        node: str | None,
        kind: str,
        timestamp,
        status: str | None = None,
        tool: str | None = None,
        error_type: str | None = None,
        retry_count: int = 0,
        duration_ms: int | None = None,
        policy_result: str | None = None,
        verification_result: str | None = None,
        payload: dict | None = None,
    ) -> AuditEvent:
        """Append one immutable audit row."""
        row = AuditEvent(
            task_id=task_id,
            run_id=run_id,
            node=node,
            tool=tool,
            kind=kind,
            status=status,
            error_type=error_type,
            retry_count=retry_count,
            duration_ms=duration_ms,
            policy_result=policy_result,
            verification_result=verification_result,
            payload=payload or {},
            ts=timestamp,
        )
        self.add(row)
        self.flush()
        return self.refresh(row)

    def list_by_task(self, task_id: UUID) -> list[AuditEvent]:
        """Full task history in replay order (seq is gapless per DB)."""
        return (
            self._session.query(AuditEvent)
            .filter(AuditEvent.task_id == task_id)
            .order_by(AuditEvent.seq.asc())
            .all()
        )

    def list_by_run(self, run_id: UUID) -> list[AuditEvent]:
        """One run's chain in replay order."""
        return (
            self._session.query(AuditEvent)
            .filter(AuditEvent.run_id == run_id)
            .order_by(AuditEvent.seq.asc())
            .all()
        )
