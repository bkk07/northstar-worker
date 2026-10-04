"""Commerce read controller: GET-only typed reads (plan §10)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.commerce.customer import CustomerRead
from app.schemas.commerce.financial import RefundRead, ReplacementRead
from app.schemas.commerce.order import OrderRead
from app.schemas.commerce.policy import PolicyRead
from app.schemas.commerce.probe import ProbeResult
from app.schemas.commerce.ticket import TicketRead
from app.services.commerce.customer_service import CustomerService
from app.services.commerce.financial_service import FinancialService
from app.services.commerce.order_service import OrderService
from app.services.commerce.policy_service import PolicyService
from app.services.commerce.probe_service import ProbeService
from app.services.commerce.ticket_service import TicketService

router = APIRouter(tags=["read"])


@router.get("/api/read/customers", response_model=list[CustomerRead])
def search_customers(q: str, session: Session = Depends(get_db)) -> list[CustomerRead]:
    """Search customers (look-alikes included)."""
    return CustomerService(session).search(q)


@router.get("/api/read/customers/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: uuid.UUID, session: Session = Depends(get_db)) -> CustomerRead:
    """One customer."""
    return CustomerService(session).get_by_id(customer_id)


@router.get("/api/read/orders", response_model=list[OrderRead])
def list_orders(customer_id: uuid.UUID, session: Session = Depends(get_db)) -> list[OrderRead]:
    """Orders of one customer."""
    return OrderService(session).list_by_customer(customer_id)


@router.get("/api/read/orders/{order_id}", response_model=OrderRead)
def get_order(order_id: uuid.UUID, session: Session = Depends(get_db)) -> OrderRead:
    """One order with items."""
    return OrderService(session).get_by_id(order_id)


@router.get("/api/read/tickets/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: uuid.UUID, session: Session = Depends(get_db)) -> TicketRead:
    """One ticket."""
    return TicketService(session).get_by_id(ticket_id)


@router.get("/api/read/replacements", response_model=list[ReplacementRead])
def list_replacements(
    order_item_id: uuid.UUID, session: Session = Depends(get_db)
) -> list[ReplacementRead]:
    """Replacements for one order item."""
    return FinancialService(session).list_replacements_by_item(order_item_id)


@router.get("/api/read/refunds", response_model=list[RefundRead])
def list_refunds(
    ticket_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    order_id: uuid.UUID | None = None,
    window_days: int = 90,
    session: Session = Depends(get_db),
) -> list[RefundRead]:
    """Refunds by ticket, customer window, or order (duplicate-trap facts)."""
    service = FinancialService(session)
    given = [v is not None for v in (ticket_id, customer_id, order_id)]
    if sum(given) != 1:
        raise HTTPException(
            status_code=422,
            detail="exactly one of ticket_id, customer_id, or order_id is required",
        )
    if ticket_id is not None:
        return service.list_refunds_by_ticket(ticket_id)
    if customer_id is not None:
        return service.list_refunds_by_customer(customer_id, window_days)
    assert order_id is not None
    return service.list_active_refunds_by_order(order_id)


@router.get("/api/read/policies", response_model=list[PolicyRead])
def list_policies(session: Session = Depends(get_db)) -> list[PolicyRead]:
    """All policy rules."""
    return PolicyService(session).list_all()


@router.get("/api/read/probe/mutation/{key}", response_model=ProbeResult)
def probe_mutation(key: str, session: Session = Depends(get_db)) -> ProbeResult:
    """Probe an idempotency key (found with identity, or not found)."""
    return ProbeService(session).probe(key)


@router.get("/api/read/probe/replacement", response_model=ProbeResult)
def probe_replacement(order_item_id: uuid.UUID, session: Session = Depends(get_db)) -> ProbeResult:
    """Probe the active replacement for an order item (business identity)."""
    return ProbeService(session).probe_replacement(order_item_id)


@router.get("/api/read/probe/refund", response_model=ProbeResult)
def probe_refund(
    ticket_id: uuid.UUID, order_id: uuid.UUID, session: Session = Depends(get_db)
) -> ProbeResult:
    """Probe the active refund for a (ticket, order) identity."""
    return ProbeService(session).probe_refund(ticket_id, order_id)
