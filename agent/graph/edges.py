"""Conditional edges: pure routing functions of state (plan §13).

Every function is deterministic and dependency-free, so the full edge
matrix is unit-testable with fake node outputs — no graph, LLM, or DB
needed. `builder.py` wires these names to node targets; unknown or
missing routing values fail closed (park or terminate, never improvise).
"""

from typing import Literal

from agent.graph.state import WorkerState
from agent.runtime import budgets

Route = str

# Hard ceiling on correction rounds (decide's own fallback fires first).
MAX_VALIDATION_FAILURES = 5


def _blown(state: WorkerState) -> bool:
    """True when a budget is already spent (edges fail closed to finalize)."""
    return budgets.exceeded(state) is not None


def route_contract(state: WorkerState) -> Route:
    """Compiler outcome: plan it, clarify it, or end inconclusive."""
    if _blown(state):
        return "finalize"
    status = state.get("contract_status", "ok")
    if status == "ambiguous":
        return "clarification"
    if status == "unsupported":
        return "finalize"
    if status == "ok":
        return "plan"
    return "finalize"


def route_validate(state: WorkerState) -> Route:
    """Invalid actions loop back with the error; anything else disposes.

    The correction loop is bounded twice: `decide` falls back to a safe
    observe after its rounds run out, and this backstop ends runs whose
    failures somehow keep climbing.
    """
    if _blown(state):
        return "finalize"
    if state.get("validation_failures", 0) > MAX_VALIDATION_FAILURES:
        return "finalize"
    status = state.get("validation_status", "ok")
    if status == "invalid":
        return "decide"
    if status == "ok":
        return "policy_check"
    return "finalize"


def route_policy(state: WorkerState) -> Route:
    """Deterministic ALLOW / HUMAN_APPROVAL / BLOCK (LLM has no vote)."""
    if _blown(state):
        return "finalize"
    outcome = state.get("policy_decision", {}).get("outcome", "")
    if outcome == "allow":
        return "execute"
    if outcome == "human_approval":
        return "human_approval"
    return "finalize"


def route_approval(state: WorkerState) -> Route:
    """Approved resumes; decided-against finalizes; pending parks (END)."""
    if _blown(state):
        return "finalize"
    status = state.get("approval_status", "pending")
    if status == "approved":
        return "execute"
    if status in ("rejected", "expired"):
        return "finalize"
    return "__end__"


def route_observe(state: WorkerState) -> Route:
    """Success continues, done verifies, failure classifies."""
    if _blown(state):
        return "finalize"
    status = state.get("observation_status", "success")
    if status == "effects_done":
        return "verify"
    if status == "failure":
        return "classify"
    if status == "success":
        return "decide"
    return "classify"


def route_recover(state: WorkerState) -> Route:
    """Router lookup: strategy name to the node that serves it."""
    if _blown(state):
        return "finalize"
    strategy = state.get("recovery", {}).get("strategy", "")
    mapping = {
        "re_observe": "observe",
        "re_discover": "observe",
        "re_plan": "plan",
        "retry": "execute",
        "probe": "probe_reconcile",
        "reconcile": "observe",
        "fallback_tool": "execute",
        "alternate_tool": "execute",
        "request_approval": "human_approval",
        "request_clarification": "clarification",
        "terminate_safely": "finalize",
    }
    return mapping.get(strategy, "finalize")


def route_probe(state: WorkerState) -> Route:
    """Reconciliation: found reconciles, absent retries, mismatch ends."""
    if _blown(state):
        return "finalize"
    status = state.get("probe_status", "exists")
    if status == "absent":
        return "execute"
    if status == "mismatch":
        return "finalize"
    if status == "exists":
        return "observe"
    return "finalize"


def route_verify(state: WorkerState) -> Route:
    """Verifier verdict: proved, retryable, or terminal."""
    if _blown(state):
        return "finalize"
    verdict = state.get("verification", {}).get("verdict", "")
    if verdict == "verified":
        return "finalize"
    if verdict == "failed":
        return "recover"
    return "finalize"


def route_clarification(state: WorkerState) -> Route:
    """Answered re-enters the compiler; otherwise the run stays parked."""
    if _blown(state):
        return "finalize"
    if state.get("clarification_status", "pending") == "answered":
        return "contract"
    return "__end__"


# Node name for a parked (waiting) run: the graph ends, the runner
# releases the lease, and resume re-enters at the waiting node.
PARKED = Literal["__end__"]
