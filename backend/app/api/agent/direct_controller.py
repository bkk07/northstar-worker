"""Agent direct-commit controller: fast path around the browser.

Same authority as `browser_submit` (the HMAC policy token over the exact
effect params), same services, same idempotency log — only the transport
differs: service-layer call instead of a Chromium form fill. The browser
stays for genuinely visual tasks; standard refunds/replacements commit
here in milliseconds.
"""

import os
import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.exceptions import ForbiddenError, NotFoundError, UnprocessableError
from app.schemas.agent.direct import DirectCommitReply, DirectCommitRequest
from app.schemas.ops.mutations import RefundCreate, ReplacementCreate
from app.services.ops.refund_service import RefundService
from app.services.ops.replacement_service import ReplacementService
from database.models.biz.order import Order, OrderItem
from database.models.biz.ticket import Ticket
from northstar_common.tokens import canonical_params_hash, verify_policy_token

router = APIRouter(tags=["agent-direct"])

# Must match the issuer default in mcp_server/context.py (both read the
# same env; local dev sets neither, so both fall back together).
_SECRET_ENV = "POLICY_TOKEN_SECRET"
_SUBMIT_ACTION = "browser_submit"
_OPERATIONAL_KEYS = frozenset({"ref", "mutation_key", "token"})


def _verify(body: DirectCommitRequest) -> None:
    """The submit token must authorize this exact (task, params) commit."""
    signable = {k: v for k, v in body.params.items() if k not in _OPERATIONAL_KEYS}
    params_hash = canonical_params_hash(signable)
    secret = os.environ.get(_SECRET_ENV, "local-policy-secret")
    if not verify_policy_token(body.token, secret, body.task_id, _SUBMIT_ACTION, params_hash):
        raise ForbiddenError("token_denied: token does not match (task, action, params)")


@router.post("/api/agent/direct/commits", response_model=DirectCommitReply)
def commit_direct(
    body: DirectCommitRequest, response: Response, session: Session = Depends(get_db)
) -> DirectCommitReply:
    """Commit a refund or replacement without the browser (201/200 replay)."""
    _verify(body)
    if body.effect == "refund.create":
        dto, created = _commit_refund(session, body)
    else:
        dto, created = _commit_replacement(session, body)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return DirectCommitReply(
        effect=body.effect,
        created=created,
        entity_id=dto.id,
        mutation_key=body.mutation_key,
        status=201 if created else 200,
    )


def _commit_refund(session: Session, body: DirectCommitRequest):
    """Resolve ids to codes, then run the standard refund service."""
    params = body.params
    order = _get_order(session, params.get("order_id", ""))
    ticket = _get_ticket(session, params.get("ticket_id", ""))
    amount = params.get("amount_paise")
    if not isinstance(amount, int) or amount <= 0:
        raise UnprocessableError("refund needs a positive amount_paise")
    return RefundService(session).create(
        RefundCreate(order_code=order.code, ticket_code=ticket.code, amount_paise=amount),
        body.mutation_key,
    )


def _commit_replacement(session: Session, body: DirectCommitRequest):
    """Resolve ids to codes + SKU, then run the standard replacement service."""
    params = body.params
    order = _get_order(session, params.get("order_id", ""))
    ticket = _get_ticket(session, params.get("ticket_id", ""))
    item = _get_item(session, order.id, params.get("order_item_id", ""))
    return ReplacementService(session).create(
        ReplacementCreate(order_code=order.code, item_sku=item.sku, ticket_code=ticket.code),
        body.mutation_key,
    )


def _get_order(session: Session, order_id: str) -> Order:
    """Order row by UUID (404 when absent or malformed)."""
    try:
        row = session.get(Order, uuid.UUID(str(order_id)))
    except (ValueError, AttributeError):
        row = None
    if row is None:
        raise NotFoundError(f"order {order_id} not found")
    return row


def _get_ticket(session: Session, ticket_id: str) -> Ticket:
    """Ticket row by UUID (404 when absent or malformed)."""
    try:
        row = session.get(Ticket, uuid.UUID(str(ticket_id)))
    except (ValueError, AttributeError):
        row = None
    if row is None:
        raise NotFoundError(f"ticket {ticket_id} not found")
    return row


def _get_item(session: Session, order_id: uuid.UUID, order_item_id: str) -> OrderItem:
    """Order item by UUID, bound to its order (404 otherwise)."""
    try:
        row = session.get(OrderItem, uuid.UUID(str(order_item_id)))
    except (ValueError, AttributeError):
        row = None
    if row is None or row.order_id != order_id:
        raise NotFoundError(f"order item {order_item_id} not on this order")
    return row
