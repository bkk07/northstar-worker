"""Audit emitter: structured audit appends from the runtime.

Nodes stay thin: they return state deltas while the runner (and, later,
recovery paths) records what happened. Each emit is its own committed
transaction — audit loss on crash is bounded to the in-flight event.
"""

from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from agent.ports.clock import ClockPort
from agent.repositories.audit_repository import AuditRepository


class AuditEmitter:
    """Append-only audit access for the runner (and later phases)."""

    def __init__(self, session_factory: Callable[[], Session], clock: ClockPort) -> None:
        self._sessions = session_factory
        self._clock = clock

    def emit(
        self,
        task_id: str,
        run_id: str | None,
        node: str | None,
        kind: str,
        status: str | None = None,
        tool: str | None = None,
        payload: dict | None = None,
        error_type: str | None = None,
        retry_count: int = 0,
        duration_ms: int | None = None,
        policy_result: str | None = None,
        verification_result: str | None = None,
    ) -> None:
        """Append one audit event (committed immediately)."""
        session = self._sessions()
        try:
            AuditRepository(session).append(
                UUID(task_id),
                UUID(run_id) if run_id else None,
                node,
                kind,
                self._clock.now(),
                status=status,
                tool=tool,
                error_type=error_type,
                retry_count=retry_count,
                duration_ms=duration_ms,
                policy_result=policy_result,
                verification_result=verification_result,
                payload=payload,
            )
            session.commit()
        finally:
            session.close()

    def node_transition(
        self,
        task_id: str,
        run_id: str,
        node: str,
        status: str | None = None,
        payload: dict | None = None,
    ) -> None:
        """One checkpointed node transition (the run's trace).

        The payload carries the uniform per-node fact — the returned
        delta keys plus the run status — so every node's visit is
        reconstructable from audit alone.
        """
        self.emit(task_id, run_id, node, "node.transition", status=status, payload=payload)

    def run_event(self, task_id: str, run_id: str, kind: str, payload: dict) -> None:
        """Run lifecycle events (`run.start`, `run.end`, `run.error`)."""
        self.emit(task_id, run_id, None, kind, payload=payload)
