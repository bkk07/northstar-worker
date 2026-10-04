"""Replacement mutation service (idempotent)."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.faults import hooks as faults
from app.repositories.commerce.order_repository import OrderRepository
from app.repositories.ops.mutation_repository import MutationRepository
from app.repositories.ops.replacement_repository import ReplacementRepository
from app.repositories.ops.ticket_repository import TicketRepository
from app.schemas.commerce.financial import ReplacementRead
from app.schemas.ops.mutations import ReplacementCreate
from app.services.commerce.financial_service import to_replacement_dto
from database.models.biz.financial import Replacement

KIND = "replacement"


class ReplacementService:
    """Create-or-replay replacements with backend business-rule checks."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._mutations = MutationRepository(session)
        self._replacements = ReplacementRepository(session)
        self._orders = OrderRepository(session)
        self._tickets = TicketRepository(session)

    def create(
        self, payload: ReplacementCreate, idempotency_key: str
    ) -> tuple[ReplacementRead, bool]:
        """Create a pending replacement, or replay the prior one.

        Returns (dto, created). Backend validation only (ownership,
        active-duplicate); worker policy lives in the agent (Phase 15).
        """
        prior = self._mutations.find_by_key(idempotency_key)
        skip_replay = faults.before_mutation("ops.replacements")
        if prior is not None and not skip_replay:
            if prior.kind != KIND:
                raise ConflictError(f"idempotency key already used for {prior.kind}")
            row = self._replacements.get_by_id(Replacement, prior.entity_id)
            if row is None:
                raise ConflictError("replacement log points to a missing row")
            return to_replacement_dto(row), False

        order = self._orders.get_by_code(payload.order_code)
        if order is None:
            raise NotFoundError(f"order {payload.order_code} not found")
        ticket = self._tickets.get_by_code(payload.ticket_code)
        if ticket is None:
            raise NotFoundError(f"ticket {payload.ticket_code} not found")
        item = self._orders.get_item(order.id, payload.item_sku)
        if item is None:
            raise NotFoundError(f"item {payload.item_sku} not on order {payload.order_code}")
        if ticket.customer_id != order.customer_id:
            raise UnprocessableError("ticket and order belong to different customers")
        if ticket.order_id is not None and ticket.order_id != order.id:
            raise UnprocessableError("ticket is linked to a different order")
        if self._replacements.find_active_by_item(item.id) is not None:
            raise ConflictError("order item already has an active replacement")
        try:
            row = self._replacements.create(
                order_id=order.id,
                order_item_id=item.id,
                customer_id=order.customer_id,
                ticket_id=ticket.id,
                mutation_key=idempotency_key,
            )
            self._mutations.record(idempotency_key, KIND, row.id)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("duplicate replacement") from exc
        faults.after_mutation("ops.replacements")
        return to_replacement_dto(row), True
