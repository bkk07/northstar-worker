"""KNOWLEDGE tools: unstructured policy/product lookup (spec Phase 7)."""

from app.services.support import support_service
from mcp_server.support import db
from mcp_server.support.envelopes import ok, require_text, run_guarded


def search_knowledge(query: str, limit: int = 10) -> dict:
    """Substring search over products, product policies, and policy rules."""
    def _call():
        q = require_text(query, "query", minimum=2, maximum=200)
        capped = max(1, min(int(limit), 25))
        with db.support_session() as session:
            return ok(results=support_service.search_knowledge(session, q=q, limit=capped))

    return run_guarded(_call)
