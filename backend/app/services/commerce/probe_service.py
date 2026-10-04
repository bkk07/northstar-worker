"""Mutation probe service (probe-before-retry support)."""

import uuid

from sqlalchemy.orm import Session

from app.repositories.commerce.financial_repository import FinancialRepository
from app.repositories.commerce.probe_repository import ProbeRepository
from app.schemas.commerce.probe import ProbeResult


class ProbeService:
    """Answer 'did this mutation already commit?' without side effects."""

    def __init__(self, session: Session) -> None:
        self._repos = ProbeRepository(session)
        self._financial = FinancialRepository(session)

    def probe(self, mutation_key: str) -> ProbeResult:
        """Probe result: found with identity, or not found (never an error)."""
        row = self._repos.find_by_key(mutation_key)
        if row is None:
            return ProbeResult(found=False)
        return ProbeResult(found=True, kind=row.kind, entity_id=row.entity_id)

    def probe_replacement(self, order_item_id: uuid.UUID) -> ProbeResult:
        """Active replacement for an order item, if any."""
        row = self._financial.find_active_replacement(order_item_id)
        if row is None:
            return ProbeResult(found=False)
        return ProbeResult(found=True, kind="replacement", entity_id=row.id)

    def probe_refund(self, ticket_id: uuid.UUID, order_id: uuid.UUID) -> ProbeResult:
        """Active refund for a (ticket, order) identity, if any."""
        row = self._financial.find_active_refund(ticket_id, order_id)
        if row is None:
            return ProbeResult(found=False)
        return ProbeResult(found=True, kind="refund", entity_id=row.id)
