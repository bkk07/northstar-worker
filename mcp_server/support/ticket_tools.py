"""TICKET tools: agent-plane reads and writes over customer tickets."""

from app.services.support import support_service
from mcp_server.support import db
from mcp_server.support.envelopes import ok, require_text, run_guarded


def get_ticket(ticket_id: str) -> dict:
    """Full ticket context: conversation, customer, order, policies."""
    def _call():
        tid = require_text(ticket_id, "ticket_id", maximum=64)
        with db.support_session() as session:
            return ok(ticket=support_service.get_ticket_detail(session, ticket_id=tid))

    return run_guarded(_call)


def add_ticket_message(
    ticket_id: str, message: str, sender_type: str = "AI_AGENT"
) -> dict:
    """Post an agent/staff/system message (terminal tickets reject)."""
    def _call():
        tid = require_text(ticket_id, "ticket_id", maximum=64)
        text = require_text(message, "message")
        sender = require_text(sender_type, "sender_type", maximum=16).upper()
        with db.support_session() as session:
            posted = support_service.add_agent_message(
                session, ticket_id=tid, sender_type=sender, message=text
            )
            return ok(message=posted)

    return run_guarded(_call)


def update_ticket(
    ticket_id: str, priority: str | None = None, category: str | None = None
) -> dict:
    """Change priority and/or category (the only agent-mutable fields)."""
    def _call():
        tid = require_text(ticket_id, "ticket_id", maximum=64)
        with db.support_session() as session:
            return ok(
                ticket=support_service.update_ticket(
                    session, ticket_id=tid, priority=priority, category=category
                )
            )

    return run_guarded(_call)


def resolve_ticket(ticket_id: str, resolution: str) -> dict:
    """Resolve with a resolution note (terminal tickets reject)."""
    def _call():
        tid = require_text(ticket_id, "ticket_id", maximum=64)
        text = require_text(resolution, "resolution", minimum=5)
        with db.support_session() as session:
            return ok(
                ticket=support_service.resolve(
                    session, staff_id="mcp-agent", ticket_id=tid, resolution=text
                )
            )

    return run_guarded(_call)


def escalate_ticket(ticket_id: str, reason: str | None = None) -> dict:
    """Escalate an actionable ticket, optional reason."""
    def _call():
        tid = require_text(ticket_id, "ticket_id", maximum=64)
        with db.support_session() as session:
            return ok(
                ticket=support_service.escalate(
                    session, staff_id="mcp-agent", ticket_id=tid, reason=reason
                )
            )

    return run_guarded(_call)
