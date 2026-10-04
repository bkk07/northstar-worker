"""Mutation probe service (probe-before-retry support)."""

from sqlalchemy.orm import Session

from app.repositories.commerce.probe_repository import ProbeRepository
from app.schemas.commerce.probe import ProbeResult


class ProbeService:
    """Answer 'did this mutation key already commit?' without side effects."""

    def __init__(self, session: Session) -> None:
        self._repos = ProbeRepository(session)

    def probe(self, mutation_key: str) -> ProbeResult:
        """Probe result: found with identity, or not found (never an error)."""
        row = self._repos.find_by_key(mutation_key)
        if row is None:
            return ProbeResult(found=False)
        return ProbeResult(found=True, kind=row.kind, entity_id=row.entity_id)
