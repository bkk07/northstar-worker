"""Evidence summary: three operator lines from verifier + journal facts.

The headline is decided, never narrated: BLOCKED / INCONCLUSIVE /
FAILED from the terminal status, and three success flavors from the
proof — DONE (verified with committed effects), VERIFIED (verified
with nothing to change), RECOVERY (a failure happened, then the proof
passed). LLM drafts are never an input; the mutation test pins that a
`llm_draft` key anywhere in the facts changes nothing.
"""

from collections.abc import Mapping


def summarize(
    status: str,
    *,
    goal: str = "",
    policy: Mapping | None = None,
    verification: Mapping | None = None,
    journal: Mapping | None = None,
    failure: Mapping | None = None,
    error: str = "",
) -> list[str]:
    """Three lines: outcome, reason code, human next step."""
    policy = policy or {}
    verification = verification or {}
    journal = journal or {}
    failure = failure or {}
    headline = _headline(status, verification, journal)
    detail = _detail(status, policy, verification, journal, failure, error)
    return [f"{headline}: {goal}".rstrip(), detail or "no further detail", _next_step(status)]


def _headline(status: str, verification: Mapping, journal: Mapping) -> str:
    """Success flavor from the proof; terminal word otherwise."""
    if status == "blocked":
        return "BLOCKED"
    if status == "inconclusive":
        return "INCONCLUSIVE"
    if status == "failed":
        return "FAILED"
    if journal.get("recovered"):
        return "RECOVERY"
    if verification.get("verdict") == "verified" and not journal.get("committed"):
        return "VERIFIED"
    return "DONE"


def _detail(
    status: str,
    policy: Mapping,
    verification: Mapping,
    journal: Mapping,
    failure: Mapping,
    error: str,
) -> str:
    """The deciding fact: rule, verdict, failure type, or recovery arc."""
    if status == "blocked" and policy.get("rule_id"):
        return f"{policy['rule_id']}: {policy.get('reason', '')}".rstrip(": ")
    if status == "failed":
        failure_type = failure.get("type", "")
        if failure_type:
            return f"{failure_type}: {(error or failure.get('type', ''))[:200]}"
        return (error or "no verification")[:300]
    if status == "inconclusive":
        return str(
            policy.get("reason", "")
            or verification.get("verdict", "")
            or "contract unsupported or ambiguous"
        )
    if journal.get("recovered"):
        arc = f"{journal.get('failure_type', 'failure')} then verified"
        strategies = journal.get("strategies") or []
        if strategies:
            arc += f" via {', '.join(str(s) for s in strategies)}"
        return arc
    if verification.get("verdict"):
        return f"verdict={verification['verdict']}"
    return "terminal status without verifier proof (preset)"


def _next_step(status: str) -> str:
    """One human action per terminal state."""
    return {
        "succeeded": "No action needed; see the journal for the committed effects.",
        "failed": "Inspect the failure type and retry or escalate to an operator.",
        "blocked": "A policy block needs an operator decision before any retry.",
        "inconclusive": "Clarify the task (contract unsupported or ambiguous).",
    }.get(status, "Clarify the task (contract unsupported or ambiguous).")
