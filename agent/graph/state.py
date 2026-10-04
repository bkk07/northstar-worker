"""Typed LangGraph state: the orchestration spine (plan §13).

One flat, JSON-serializable dict flows through every node, so any
checkpoint row fully describes a run. Routing helpers (`contract_status`,
`validation_status`, `observation_status`, `probe_status`,
`approval_status`, `clarification_status`) are set by nodes and read only
by the pure routing functions in `edges.py`. Later phases fill the
payload fields (contract, plan, memory, budgets); Phase 12 only needs
every edge to be routable with fake node outputs.
"""

from typing import Literal, TypedDict

# Routing vocabularies. Unknown values fail closed (route to a safe end).
ContractStatus = Literal["ok", "ambiguous", "unsupported"]
ValidationStatus = Literal["ok", "invalid"]
ObservationStatus = Literal["success", "effects_done", "failure"]
ProbeStatus = Literal["exists", "absent", "mismatch"]
ApprovalStatus = Literal["approved", "rejected", "pending"]
ClarificationStatus = Literal["answered", "pending"]


class FailureInfo(TypedDict, total=False):
    """What went wrong and how often (classifier owns `type`)."""

    type: str
    count: int


class RecoveryInfo(TypedDict, total=False):
    """Chosen strategy plus per-strategy counters (router owns)."""

    strategy: str
    counters: dict[str, int]


class PolicyDecisionInfo(TypedDict, total=False):
    """Deterministic ALLOW / HUMAN_APPROVAL / BLOCK outcome."""

    outcome: str
    rule_id: str
    reason: str


class BudgetInfo(TypedDict, total=False):
    """Consumed vs configured budgets (guards run on every edge)."""

    used: dict[str, float]
    limits: dict[str, float]


class WorkerState(TypedDict, total=False):
    """Full run state. All values must stay JSON-serializable."""

    task_id: str
    run_id: str
    task_text: str
    contract: dict
    contract_status: str
    plan: list
    cursor: int
    memory_refs: list[str]
    last_action: dict
    last_observation: dict
    observation_status: str
    failure: FailureInfo
    recovery: RecoveryInfo
    validation_status: str
    validation_error: str
    policy_decision: PolicyDecisionInfo
    approval_ref: dict
    approval_status: str
    clarification_ref: dict
    clarification_status: str
    probe_status: str
    verification: dict
    budgets: BudgetInfo
    status: str


def initial_state(task_id: str, run_id: str, task_text: str) -> WorkerState:
    """Seed state for a fresh run (runner owns leases; graph owns flow)."""
    return WorkerState(task_id=task_id, run_id=run_id, task_text=task_text, status="pending")
