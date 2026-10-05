"""Finalization mapping: decided outcome to terminal status (pure)."""

from agent.services.finalization_service import final_status, summarize


def _state(**overrides):
    return {"task_text": "replace the damaged laptop", **overrides}


def test_verified_maps_to_succeeded():
    """The hero path ends SUCCEEDED."""
    state = _state(verification={"verdict": "verified"})
    assert final_status(state) == "succeeded"


def test_policy_block_maps_to_blocked():
    """BLOCK ends without touching tools."""
    state = _state(policy_decision={"outcome": "block", "rule_id": "P-REF-004"})
    assert final_status(state) == "blocked"


def test_rejected_approval_maps_to_blocked():
    """A decided-against approval blocks the task."""
    state = _state(approval_status="rejected")
    assert final_status(state) == "blocked"


def test_unsupported_contract_maps_to_inconclusive():
    """No registry effect fits: inconclusive, never improvised."""
    state = _state(contract_status="unsupported")
    assert final_status(state) == "inconclusive"


def test_failed_verification_maps_to_failed():
    """A failed proof fails the run (recovery decides the retry)."""
    state = _state(verification={"verdict": "failed"})
    assert final_status(state) == "failed"


def test_summary_has_three_lines():
    """The evidence draft always renders outcome, reason, next step."""
    lines = summarize(_state(verification={"verdict": "verified"}))
    assert len(lines) == 3
    assert lines[0].startswith("DONE")
    assert "No action needed" in lines[2]


def test_blocked_summary_names_rule():
    """Blocked summaries carry the rule for the operator."""
    lines = summarize(
        _state(policy_decision={"outcome": "block", "rule_id": "P-REF-004", "reason": "too big"})
    )
    assert lines[0].startswith("BLOCKED")
    assert "P-REF-004" in lines[1]
