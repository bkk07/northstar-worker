"""Canonical support-ticket LangGraph (supervisor → workflow → HITL → verify).

This is the ONE execution path used by `POST /support/tickets/:id/solve`.
The legacy direct `runner.run_ticket` path is deprecated; `agent_run_service`
delegates to `runner.run_support_ticket` here.
"""

from agent.support_graph.graph import build_support_graph
from agent.support_graph.runner import resume_support_ticket, run_support_ticket
from agent.support_graph.state import SupportGraphState, fresh_graph_state

__all__ = [
    "SupportGraphState",
    "build_support_graph",
    "fresh_graph_state",
    "resume_support_ticket",
    "run_support_ticket",
]
