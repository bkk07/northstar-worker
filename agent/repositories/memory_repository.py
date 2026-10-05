"""Memory repository: working-memory rows with provenance (`worker.memory_items`)."""

from uuid import UUID

from agent.repositories.base import BaseRepository
from database.models.worker.memory import MemoryItem


class MemoryRepository(BaseRepository[MemoryItem]):
    """`ns_runner`-role memory writes (observations and contracts only)."""

    def record(
        self,
        run_id: UUID,
        key: str,
        value: dict,
        source_type: str,
        trust: str,
        source_ref: str | None = None,
        confidence: float | None = None,
    ) -> MemoryItem:
        """Append one sourced fact (every item needs a source and trust)."""
        if not source_type:
            raise ValueError("memory items require a source_type")
        if trust not in ("trusted", "untrusted"):
            raise ValueError(f"memory trust must be trusted/untrusted, got {trust!r}")
        row = MemoryItem(
            run_id=run_id,
            key=key,
            value=dict(value),
            source_type=source_type,
            source_ref=source_ref,
            trust=trust,
            confidence=confidence,
        )
        self.add(row)
        self.flush()
        return self.refresh(row)

    def list_by_run(self, run_id: UUID) -> list[MemoryItem]:
        """Every memory item for a run, oldest first."""
        return (
            self._session.query(MemoryItem)
            .filter(MemoryItem.run_id == run_id)
            .order_by(MemoryItem.created_at, MemoryItem.id)
            .all()
        )

    def list_trusted(self, run_id: UUID) -> list[MemoryItem]:
        """Trusted items only (the only ones decisions may rely on)."""
        return [row for row in self.list_by_run(run_id) if row.trust == "trusted"]
