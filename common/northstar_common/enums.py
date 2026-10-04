"""Shared domain vocabulary (pure Python, dependency-free).

The sandbox (backend), the agent, and the verifier must agree on these
states and types, so they live in `common` and nowhere else. Every enum
is a `str` enum: values go to Postgres, JSON, and audit logs unchanged.

References: NORTHSTAR_WORKER_FINAL_PLAN §3 (enums), §16 (policy),
§17 (failures), §20 (verdicts), §22 (memory).
"""

from enum import StrEnum


class TaskState(StrEnum):
    """Lifecycle of a worker task (mirrors `worker.tasks.status`)."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    WAITING_FOR_CLARIFICATION = "waiting_for_clarification"
    WAITING_ON_CUSTOMER = "waiting_on_customer"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    INCONCLUSIVE = "inconclusive"
    CANCELLED = "cancelled"


class FailureType(StrEnum):
    """Deterministic failure taxonomy (plan §17, 14 types)."""

    NETWORK_ERROR = "network_error"
    UNKNOWN_OUTCOME = "unknown_outcome"
    ELEMENT_NOT_FOUND = "element_not_found"
    DOM_CHANGED = "dom_changed"
    VALIDATION_ERROR = "validation_error"
    DUPLICATE_OPERATION = "duplicate_operation"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    AMBIGUOUS_REQUEST = "ambiguous_request"
    UNSAFE_ACTION = "unsafe_action"
    SESSION_EXPIRED = "session_expired"
    POLICY_BLOCKED = "policy_blocked"
    TIMEOUT = "timeout"
    BUDGET_EXCEEDED = "budget_exceeded"


class PolicyOutcome(StrEnum):
    """Authorization verdict: may the worker act autonomously?"""

    ALLOW = "allow"
    HUMAN_APPROVAL = "human_approval"
    BLOCK = "block"


class PolicyRuleId(StrEnum):
    """Versioned rule identifiers (plan §16). E-* are eligibility
    (is the customer entitled?), P-* are authorization (may the worker?)."""

    E_REPL_001 = "E-REPL-001"
    E_REF_001 = "E-REF-001"
    E_REF_002 = "E-REF-002"
    P_CAP_001 = "P-CAP-001"
    P_OWN_001 = "P-OWN-001"
    P_REF_001 = "P-REF-001"
    P_REF_002 = "P-REF-002"
    P_REF_003 = "P-REF-003"
    P_REF_004 = "P-REF-004"
    P_REPL_001 = "P-REPL-001"
    P_REPL_002 = "P-REPL-002"
    P_NOTE_001 = "P-NOTE-001"
    P_DUP_001 = "P-DUP-001"
    P_FAIL_CLOSED = "P-FAIL-CLOSED"


class Verdict(StrEnum):
    """Independent verifier outcome, from real DB state only (plan §20)."""

    VERIFIED = "verified"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class EffectType(StrEnum):
    """Business effects the worker may produce. Closed set: anything outside
    this registry is rejected by the contract compiler (plan §13, §28)."""

    REPLACEMENT_CREATE = "replacement.create"
    REFUND_CREATE = "refund.create"
    TICKET_NOTE = "ticket.note"
    TICKET_STATUS = "ticket.status"
    TICKET_REPLY = "ticket.reply"


class RecoveryAction(StrEnum):
    """Distinct recovery moves the router may choose (plan §17, 11 actions)."""

    RE_OBSERVE = "re_observe"
    RE_DISCOVER = "re_discover"
    RE_PLAN = "re_plan"
    RETRY = "retry"
    PROBE = "probe"
    RECONCILE = "reconcile"
    FALLBACK_TOOL = "fallback_tool"
    ALTERNATE_TOOL = "alternate_tool"
    REQUEST_APPROVAL = "request_approval"
    REQUEST_CLARIFICATION = "request_clarification"
    TERMINATE_SAFELY = "terminate_safely"


class MemorySourceType(StrEnum):
    """Provenance of a working-memory item (plan §22)."""

    USER = "user"
    OPERATOR = "operator"
    TICKET = "ticket"
    DATABASE = "database"
    API = "api"
    PAGE = "page"
    BROWSER = "browser"
    POLICY = "policy"


class MemoryTrust(StrEnum):
    """Trust level: untrusted facts need a DB cross-check before use."""

    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class TicketStatus(StrEnum):
    """Ticket lifecycle in the commerce sandbox (`biz.tickets.status`)."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_ON_CUSTOMER = "waiting_on_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketNoteKind(StrEnum):
    """Internal notes never reach the customer; replies do."""

    INTERNAL = "internal"
    CUSTOMER_REPLY = "customer_reply"


# Convenience groupings used by later phases (graph edges, resume rules).
TERMINAL_TASK_STATES = frozenset(
    {
        TaskState.SUCCEEDED,
        TaskState.FAILED,
        TaskState.BLOCKED,
        TaskState.INCONCLUSIVE,
        TaskState.CANCELLED,
    }
)

WAITING_TASK_STATES = frozenset(
    {
        TaskState.WAITING_FOR_APPROVAL,
        TaskState.WAITING_FOR_CLARIFICATION,
        TaskState.WAITING_ON_CUSTOMER,
    }
)
