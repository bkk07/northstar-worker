"""Evidence packet builder: one terminal run, fully reconstructable.

The packet assembles verifier output, journal commits, policy
decisions, recovery history, memory provenance, screenshots, and an
audit pointer — every section from database rows or the final graph
state, never from LLM prose. `reconstruct_chain` replays a run's node
order from its audit events alone.
"""

from collections.abc import Mapping, Sequence

from agent.evidence import summary as evidence_summary

PACKET_VERSION = "evidence/v1"


def build_packet(
    *,
    task_id: str,
    run_id: str,
    task_text: str,
    status: str,
    goal: str = "",
    effects: Sequence[Mapping] | None = None,
    policy: Mapping | None = None,
    policy_history: Sequence[Mapping] | None = None,
    verification: Mapping | None = None,
    journal: Mapping | None = None,
    memory: Mapping | None = None,
    screenshots: Sequence[Mapping] | None = None,
    audit: Mapping | None = None,
    failure: Mapping | None = None,
    error: str = "",
) -> dict:
    """Assemble the packet; the summary derives from facts only."""
    policy = policy or {}
    verification = verification or {}
    journal = journal or {}
    memory = memory or {}
    audit = audit or {}
    lines = evidence_summary.summarize(
        status,
        goal=goal or task_text,
        policy=policy,
        verification=verification,
        journal=journal,
        failure=failure,
        error=error,
    )
    return {
        "version": PACKET_VERSION,
        "task_id": task_id,
        "run_id": run_id,
        "task_text": task_text,
        "status": status,
        "summary": lines,
        "goal": goal or task_text,
        "effects": [dict(effect) for effect in (effects or [])],
        "policy": {
            "decision": dict(policy),
            "history": [dict(entry) for entry in (policy_history or [])],
        },
        "verification": dict(verification),
        "journal": {
            "committed": list(journal.get("committed", [])),
            "recovered": bool(journal.get("recovered", False)),
            "failure_type": journal.get("failure_type", ""),
            "strategies": list(journal.get("strategies", [])),
        },
        "memory": {
            "item_count": memory.get("item_count", 0),
            "trusted": memory.get("trusted", 0),
            "untrusted": memory.get("untrusted", 0),
            "injection_flags": list(memory.get("injection_flags", [])),
        },
        "screenshots": [dict(shot) for shot in (screenshots or [])],
        "audit": {
            "events": audit.get("events", 0),
            "first_seq": audit.get("first_seq"),
            "last_seq": audit.get("last_seq"),
        },
    }


def reconstruct_chain(events: Sequence[Mapping]) -> list[str]:
    """Node order for a run from its audit events (seq order, no gaps)."""
    ordered = sorted(events, key=lambda event: (event.get("seq") or 0, str(event.get("id", ""))))
    chain: list[str] = []
    for event in ordered:
        node = event.get("node")
        if event.get("kind") in ("node.transition", "node.done") and node and node not in chain:
            chain.append(str(node))
    return chain
