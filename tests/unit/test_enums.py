"""Phase 3: shared enums are documented and match the plan's closed sets."""

from northstar_common import enums
from northstar_common.enums import (
    EffectType,
    FailureType,
    MemorySourceType,
    MemoryTrust,
    PolicyOutcome,
    PolicyRuleId,
    RecoveryAction,
    TaskState,
    TicketNoteKind,
    TicketStatus,
    Verdict,
)


def test_all_enums_documented():
    for name in [
        "TaskState",
        "FailureType",
        "PolicyOutcome",
        "PolicyRuleId",
        "Verdict",
        "EffectType",
        "RecoveryAction",
        "MemorySourceType",
        "MemoryTrust",
        "TicketStatus",
        "TicketNoteKind",
    ]:
        assert getattr(enums, name).__doc__, f"{name} must be documented"


def test_failure_taxonomy_has_14_types():
    assert len(FailureType) == 14
    assert FailureType.UNKNOWN_OUTCOME.value == "unknown_outcome"
    assert FailureType.POLICY_BLOCKED.value == "policy_blocked"


def test_recovery_actions_have_11_moves():
    assert len(RecoveryAction) == 11
    assert RecoveryAction.PROBE.value == "probe"
    assert RecoveryAction.TERMINATE_SAFELY.value == "terminate_safely"


def test_policy_outcomes_and_rule_ids():
    assert {o.value for o in PolicyOutcome} == {"allow", "human_approval", "block"}
    rule_ids = {r.value for r in PolicyRuleId}
    assert {"P-REF-004", "P-OWN-001", "P-CAP-001", "P-FAIL-CLOSED"} <= rule_ids
    assert {"E-REPL-001", "E-REF-001", "E-REF-002"} <= rule_ids


def test_verdicts_and_effects():
    assert {v.value for v in Verdict} == {"verified", "failed", "inconclusive"}
    assert {e.value for e in EffectType} == {
        "replacement.create",
        "refund.create",
        "ticket.note",
        "ticket.status",
        "ticket.reply",
    }


def test_task_state_groupings():
    assert TaskState.SUCCEEDED in enums.TERMINAL_TASK_STATES
    assert TaskState.RUNNING not in enums.TERMINAL_TASK_STATES
    assert TaskState.WAITING_FOR_APPROVAL in enums.WAITING_TASK_STATES
    assert enums.TERMINAL_TASK_STATES.isdisjoint(enums.WAITING_TASK_STATES)


def test_ticket_and_memory_types():
    assert len(TicketStatus) == 5
    assert TicketStatus.RESOLVED.value == "resolved"
    assert {k.value for k in TicketNoteKind} == {"internal", "customer_reply"}
    assert MemoryTrust.UNTRUSTED.value == "untrusted"
    assert MemorySourceType.POLICY.value == "policy"
