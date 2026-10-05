"""Memory store: sourced writes and trust-filtered reads (Phase 23).

Items are written only by `observe` and `contract` — never from LLM
free text — and each points at a journal action. Untrusted items need a
deterministic cross-check against a database fact before any decision
may use them; the cross-check becomes its own trusted item.
"""

from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from agent.memory import provenance
from agent.repositories.memory_repository import MemoryRepository


class MemoryStore:
    """Run-scoped working memory over `worker.memory_items`."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._sessions = session_factory

    def record(
        self,
        run_id: str,
        key: str,
        value: dict,
        source_type: str,
        source_ref: str | None = None,
        confidence: float | None = None,
        trust: str | None = None,
    ) -> dict:
        """Append one item; trust defaults to the source classification."""
        session = self._sessions()
        try:
            row = MemoryRepository(session).record(
                UUID(run_id),
                key,
                value,
                source_type,
                trust or provenance.classify(source_type),
                source_ref=source_ref,
                confidence=confidence,
            )
            session.commit()
            return {
                "key": row.key,
                "value": dict(row.value or {}),
                "source_type": row.source_type,
                "source_ref": row.source_ref,
                "trust": row.trust,
            }
        finally:
            session.close()

    def cross_check(
        self,
        run_id: str,
        key: str,
        value: dict,
        untrusted_ref: str,
        source_ref: str | None = None,
    ) -> dict:
        """Promote an untrusted fact via a database cross-check (new item)."""
        return self.record(
            run_id,
            key,
            {**value, "cross_checked": untrusted_ref},
            "database",
            source_ref=source_ref,
            trust=provenance.TRUSTED,
        )

    def items(self, run_id: str) -> list[dict]:
        """Every item for a run, oldest first (prompt block source)."""
        session = self._sessions()
        try:
            return [
                {
                    "key": row.key,
                    "value": dict(row.value or {}),
                    "source_type": row.source_type,
                    "source_ref": row.source_ref,
                    "trust": row.trust,
                }
                for row in MemoryRepository(session).list_by_run(UUID(run_id))
            ]
        finally:
            session.close()

    def trusted(self, run_id: str) -> list[dict]:
        """Trusted items only (the only ones decisions may rely on)."""
        return [item for item in self.items(run_id) if item["trust"] == "trusted"]

    def recent(self, run_id: str, limit: int = 10) -> list[dict]:
        """Newest items first, capped (checkpoint-safe prompt source)."""
        return list(reversed(self.items(run_id)))[-limit:]
