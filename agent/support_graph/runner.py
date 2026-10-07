"""Run + resume the canonical support graph (no worker-task detour).

The runner streams node transitions so the service layer can persist
tool calls, audit events, and the full `graph_state` snapshot. The snapshot
is what makes resume real: `resume_support_ticket` reloads it instead of
restarting from scratch.
"""

import json
from collections.abc import Callable

from agent.support_graph.graph import build_support_graph
from agent.support_graph.state import SupportGraphState, fresh_graph_state


def _jsonable(value):
    return json.loads(json.dumps(value, default=str))


def run_support_ticket(
    ticket_id: str,
    *,
    tools: dict,
    llm=None,
    initial_state: dict | None = None,
    on_node: Callable[[str, dict], None] | None = None,
    max_steps: int = 40,
) -> dict:
    """Execute the support graph to pause (HITL) or terminal state."""
    graph = build_support_graph(tools=tools, llm=llm)
    merged: dict = _jsonable(initial_state or fresh_graph_state(ticket_id))
    merged.setdefault("ticket_id", ticket_id)
    steps = 0
    try:
        for chunk in graph.stream(dict(merged), stream_mode="updates"):
            for node, delta in chunk.items():
                if isinstance(delta, dict):
                    merged.update(_jsonable(delta))
                steps += 1
                if on_node is not None:
                    on_node(node, dict(merged))
                if steps >= max_steps:
                    merged["decision"] = merged.get("decision") or "needs_human"
                    merged["error"] = f"step cap hit ({max_steps})"
                    merged["escalated"] = True
                    return merged
    except Exception as exc:
        merged["decision"] = "needs_human"
        merged["escalated"] = True
        merged["error"] = str(exc)[:500]
        return merged
    return merged


def resume_support_ticket(
    saved_state: dict,
    *,
    tools: dict,
    llm=None,
    approval_status: str | None = None,
    human_feedback: str | None = None,
    on_node: Callable[[str, dict], None] | None = None,
) -> dict:
    """Resume SAME execution after HITL with the human decision injected."""
    resumed = _jsonable(saved_state)
    if approval_status is not None:
        resumed["approval_status"] = approval_status
    if human_feedback is not None:
        resumed["human_feedback"] = human_feedback
    # Skip already-completed prefix: start from the approval gate forward.
    # The graph is deterministic; re-running prefix nodes is idempotent
    # (reads only), so resume replays them cheaply then continues.
    ticket_id = resumed.get("ticket_id", "")
    return run_support_ticket(
        ticket_id, tools=tools, llm=llm, initial_state=resumed, on_node=on_node
    )


def is_paused_for_human(state: dict) -> bool:
    """True when the graph parked at the HITL gate awaiting a decision."""
    return bool(state.get("approval_required")) and state.get("approval_status") in (
        None,
        "pending",
    )
