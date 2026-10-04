"""Refund mutation service (idempotent)."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.repositories.commerce.order_repository import OrderRepository
from app.repositories.ops.mutation_repository import MutationRepository
from app.repositories.ops.refund_repository import RefundRepository
from app.repositories.ops.ticket_repository import TicketRepository
from app.schemas.commerce.financial import RefundRead
from app.schemas.ops.mutations import RefundCreate
from app.services.commerce.financial_service import to_refund_dto
from database.models.biz.financial import Refund

KIND = "refund"


class RefundService:
    """Create-or-replay refunds with backend business-rule checks."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._mutations = MutationRepository(session)
        self._refunds = RefundRepository(session)
        self._orders = OrderRepository(session)
        self._tickets = TicketRepository(session)

    def create(self, payload: RefundCreate, idempotency_key: str) -> tuple[RefundRead, bool]:
        """Create a pending refund, or replay the prior one.

        Returns (dto, created). Ownership and paid-cap are enforced here;
        worker authorization lives in the agent (Phase 15).
        """
        prior = self._mutations.find_by_key(idempotency_key)
        if prior is not None:
            if prior.kind != KIND:
                raise ConflictError(f"idempotency key already used for {prior.kind}")
            row = self._refunds.get_by_id(Refund, prior.entity_id)
            if row is None:
                raise ConflictError("refund log points to a missing row")
            return to_refund_dto(row), False

        order = self._orders.get_by_code(payload.order_code)
        if order is None:
            raise NotFoundError(f"order {payload.order_code} not found")
        ticket = self._tickets.get_by_code(payload.ticket_code)
        if ticket is None:
            raise NotFoundError(f"ticket {payload.ticket_code} not found")
        if ticket.customer_id != order.customer_id:
            raise UnprocessableError("ticket and order belong to different customers")
        if ticket.order_id is not None and ticket.order_id != order.id:
            raise UnprocessableError("ticket is linked to a different order")
        already = self._refunds.sum_active_for_order(order.id)
        if already + payload.amount_paise > order.paid_paise:
            raise UnprocessableError("refund exceeds amount paid on the order")
        try:
            row = self._refunds.create(
                order_id=order.id,
                customer_id=order.customer_id,
                ticket_id=ticket.id,
                amount_paise=payload.amount_paise,
                mutation_key=idempotency_key,
            )
            self._mutations.record(idempotency_key, KIND, row.id)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("duplicate refund") from exc
        return to_refund_dto(row), True
