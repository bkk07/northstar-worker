"""ACTION tools: idempotent mock executions (spec Phase 7 ACTIONS).

Every tool takes a caller-chosen `mutation_key`: retries with the same key
collide (409 → failure envelope) instead of duplicating, so the Phase 8/9
agent can safely retry. Amounts default sensibly (refund → order total).
"""

from app.services.actions import action_service
from mcp_server.support import db
from mcp_server.support.envelopes import ok, parse_uuid, require_text, run_guarded


def _execute(
    action_type: str,
    order_id: str,
    mutation_key: str,
    ticket_id: str | None,
    amount_paise: int | None,
) -> dict:
    def _call():
        oid = parse_uuid(order_id, "order_id")
        key = require_text(mutation_key, "mutation_key", maximum=64)
        tid = None
        if ticket_id is not None:
            tid = str(parse_uuid(ticket_id, "ticket_id"))
        with db.support_session() as session:
            action = action_service.execute_action(
                session,
                action_type=action_type,
                order_id=str(oid),
                ticket_id=tid,
                mutation_key=key,
                amount_paise=amount_paise,
            )
            return ok(action=action)

    return run_guarded(_call)


def mock_refund(
    order_id: str, mutation_key: str, ticket_id: str | None = None,
    amount_paise: int | None = None,
) -> dict:
    """Record a mock refund against a paid order."""
    return _execute("REFUND", order_id, mutation_key, ticket_id, amount_paise)


def mock_return(
    order_id: str, mutation_key: str, ticket_id: str | None = None
) -> dict:
    """Record a mock return and mark the order RETURNED."""
    return _execute("RETURN", order_id, mutation_key, ticket_id, None)


def mock_replace(
    order_id: str, mutation_key: str, ticket_id: str | None = None
) -> dict:
    """Record a mock replacement for a delivered order."""
    return _execute("REPLACE", order_id, mutation_key, ticket_id, None)


def mock_cancel_order(
    order_id: str, mutation_key: str, ticket_id: str | None = None
) -> dict:
    """Cancel a PROCESSING order and mark it CANCELLED."""
    return _execute("CANCEL", order_id, mutation_key, ticket_id, None)
