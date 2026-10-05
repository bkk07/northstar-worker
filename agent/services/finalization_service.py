"""Finalization service: terminal status plus the evidence summary draft.

The mapping from decided outcome to terminal task state is the stable
contract (topology tests pin it through this pure function); Phase 24
builds the full evidence packet around it. Summaries are templated from
structured facts — an optional LLM paragraph may narrate, never decide.
"""

from collections.abc import Mapping

TERMINAL_STATUSES = ("succeeded", "failed", "blocked", "inconclusive")


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
    """Terminal mapping plus summaries (no persistence; the runner owns rows)."""

    def status(self, state: Mapping) -> str:
        """Terminal status for a final graph state."""
        return final_status(state)

    def summary(self, state: Mapping) -> list[str]:
        """Three-line evidence draft for a final graph state."""
        return summarize(state)
