"""Finalization service: terminal status plus the evidence packet.

The mapping from decided outcome to terminal task state is the stable
contract (topology tests pin it through this pure function); `summarize`
stays the pinned three-line draft. `build_packet` (Phase 24) assembles
the full evidence packet from verifier output, journal rows, policy
decisions, recovery audit, memory provenance, and screenshots — every
section from database rows or the final graph state, never LLM prose.
The runner persists the packet; this service never writes.
"""

from collections.abc import Callable, Mapping
from uuid import UUID

from sqlalchemy.orm import Session

from agent.evidence import builder as evidence_builder
from agent.repositories.audit_repository import AuditRepository
from agent.repositories.evidence_repository import EvidenceRepository
from agent.repositories.journal_repository import JournalRepository
from agent.repositories.memory_repository import MemoryRepository
from agent.repositories.policy_decision_repository import PolicyDecisionRepository

TERMINAL_STATUSES = ("succeeded", "failed", "blocked", "inconclusive")

COMMITTED_JOURNAL = frozenset({"done", "reconciled"})


def final_status(state: Mapping) -> str:
    """Fold the decided outcome into a terminal status (deterministic)."""
    if state.get("status") in TERMINAL_STATUSES:
        return str(state["status"])
    if state.get("approval_status") == "rejected":
        return "blocked"
    if state.get("policy_decision", {}).get("outcome") == "block":
        return "blocked"
    if state.get("contract_status") == "unsupported":
        return "inconclusive"
    if state.get("probe_status") == "mismatch":
        return "inconclusive"
    verdict = state.get("verification", {}).get("verdict", "")
    if verdict == "failed":
        return "failed"
    if verdict == "inconclusive":
        return "inconclusive"
    if verdict == "verified":
        return "succeeded"
    return "inconclusive"


def summarize(state: Mapping) -> list[str]:
    """Three operator lines: outcome, reason code, human next step."""
    status = final_status(state)
    policy = state.get("policy_decision", {})
    rule = policy.get("rule_id", "")
    reason = policy.get("reason", "")
    contract = state.get("contract", {})
    goal = contract.get("goal", state.get("task_text", "")) if isinstance(contract, dict) else ""
    headline = {
        "succeeded": "DONE",
        "failed": "FAILED",
        "blocked": "BLOCKED",
        "inconclusive": "INCONCLUSIVE",
    }[status]
    failure = state.get("failure", {})
    if status == "failed" and failure.get("type"):
        detail = f"{failure['type']}: {state.get('error', failure.get('type'))}"
    elif status == "failed" and state.get("error"):
        detail = str(state["error"])[:300]
    elif rule:
        detail = f"{rule}: {reason}"
    else:
        detail = str(state.get("verification", {}).get("verdict", "no verification"))
    next_step = {
        "succeeded": "No action needed; see the journal for the committed effects.",
        "failed": "Inspect the failure type and retry or escalate to an operator.",
        "blocked": "A policy block needs an operator decision before any retry.",
        "inconclusive": "Clarify the task (contract unsupported or ambiguous).",
    }[status]
    return [f"{headline}: {goal}".rstrip(), detail or "no further detail", next_step]


class FinalizationService:
    """Terminal mapping, summaries, and packet assembly (no persistence)."""

    def status(self, state: Mapping) -> str:
        """Terminal status for a final graph state."""
        return final_status(state)

    def summary(self, state: Mapping) -> list[str]:
        """Three-line evidence draft for a final graph state."""
        return summarize(state)

    def build_packet(
        self,
        sessions: Callable[[], Session],
        task_id: str,
        run_id: str,
        state: Mapping,
    ) -> dict:
        """Assemble the terminal packet from rows + final state (pure read)."""
        session = sessions()
        try:
            run_key = UUID(run_id)
            actions = JournalRepository(session).list_by_run(run_key)
            decisions = PolicyDecisionRepository(session).list_by_run(run_key)
            events = AuditRepository(session).list_by_run(run_key)
            memory_items = MemoryRepository(session).list_by_run(run_key)
            shots = [
                row
                for row in EvidenceRepository(session).screenshots_for_task(UUID(task_id))
                if (row.packet or {}).get("run_id") == run_id
            ]
        finally:
            session.close()
        journal = _journal_facts(actions, events, state)
        contract = state.get("contract", {})
        contract = contract if isinstance(contract, dict) else {}
        policy = state.get("policy_decision", {})
        policy = policy if isinstance(policy, dict) else {}
        verification = state.get("verification", {})
        verification = verification if isinstance(verification, dict) else {}
        failure = state.get("failure", {})
        failure = failure if isinstance(failure, dict) else {}
        seqs = [event.seq for event in events if event.seq is not None]
        return evidence_builder.build_packet(
            task_id=task_id,
            run_id=run_id,
            task_text=str(state.get("task_text", "")),
            status=str(state.get("status", "")),
            goal=str(contract.get("goal", "")),
            effects=contract.get("effects", []),
            policy=policy,
            policy_history=[
                {"outcome": row.outcome, "rule_id": row.rule_id, "reason": row.reason}
                for row in decisions
            ],
            verification=verification,
            journal=journal,
            memory=_memory_digest(memory_items),
            screenshots=[
                {
                    "run_id": run_id,
                    "label": (row.packet or {}).get("label", ""),
                    "path": (row.packet or {}).get("path", ""),
                }
                for row in shots
            ],
            audit={
                "events": len(events),
                "first_seq": min(seqs) if seqs else None,
                "last_seq": max(seqs) if seqs else None,
            },
            failure=failure,
            error=str(state.get("error", "")),
        )


def _journal_facts(actions, events, state: Mapping) -> dict:
    """Commit list + recovery arc from journal rows and recovery audit."""
    committed = [
        f"{action.tool}:{action.mutation_key or 'unkeyed'}"
        for action in actions
        if action.status in COMMITTED_JOURNAL
    ]
    recovery_rounds = [event for event in events if event.kind == "recovery.decided"]
    counters = state.get("recovery", {}).get("counters", {})
    counters = counters if isinstance(counters, dict) else {}
    return {
        "committed": committed,
        "recovered": bool(recovery_rounds) or any(counters.values()),
        "failure_type": next(
            (event.error_type or "" for event in recovery_rounds if event.error_type),
            "",
        ),
        "strategies": [event.status or "" for event in recovery_rounds if event.status],
    }


def _memory_digest(items) -> dict:
    """Provenance counts plus injection flags (no raw page text)."""
    trusted = sum(1 for item in items if item.trust == "trusted")
    flags: list[str] = []
    for item in items:
        if str(item.key).startswith("injection:flag:"):
            value = item.value or {}
            flags.extend(str(flag) for flag in value.get("flags", []))
    return {
        "item_count": len(items),
        "trusted": trusted,
        "untrusted": len(items) - trusted,
        "injection_flags": sorted(set(flags)),
    }
