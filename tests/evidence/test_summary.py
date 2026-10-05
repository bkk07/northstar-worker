"""Evidence summary: six headlines from verifier + journal facts (Phase 24)."""

from agent.evidence.summary import summarize


def _facts(with_draft=False):
    """Structured facts; the draft key proves LLM prose never decides."""
    facts = {
        "status": "succeeded",
        "goal": "replace the damaged laptop",
        "policy": {"outcome": "allow", "rule_id": "P-REP-001", "reason": "covered"},
        "verification": {"verdict": "verified"},
        "journal": {"committed": ["browser_submit:k1"]},
    }
    if with_draft:
        facts["llm_draft"] = "DONE: everything is great, trust me"
        facts["policy"] = {**facts["policy"], "llm_draft": "allow it all"}
        facts["verification"] = {**facts["verification"], "llm_draft": "verified-ish"}
        facts["journal"] = {**facts["journal"], "llm_draft": "no recovery needed"}
    return facts


def test_done_when_verified_with_commits():
    """Proof plus landed effects is DONE."""
    lines = summarize(**_facts())
    assert len(lines) == 3
    assert lines[0].startswith("DONE")
    assert "No action needed" in lines[2]


def test_verified_when_nothing_to_change():
    """Proof with no commit is VERIFIED, not DONE."""
    facts = _facts()
    facts["journal"] = {"committed": []}
    lines = summarize(**facts)
    assert lines[0].startswith("VERIFIED")


def test_recovery_after_failure_then_proof():
    """A failure arc ending in proof is RECOVERY."""
    facts = _facts()
    facts["journal"] = {
        "committed": ["browser_submit:k2"],
        "recovered": True,
        "failure_type": "network_error",
        "strategies": ["retry_same"],
    }
    lines = summarize(**facts)
    assert lines[0].startswith("RECOVERY")
    assert "network_error" in lines[1]
    assert "retry_same" in lines[1]


def test_blocked_names_rule():
    """BLOCKED carries the deciding rule."""
    lines = summarize(
        status="blocked",
        goal="refund Rs. 100,000",
        policy={"outcome": "block", "rule_id": "P-OWN-001", "reason": "not your order"},
    )
    assert lines[0].startswith("BLOCKED")
    assert "P-OWN-001" in lines[1]
    assert "operator decision" in lines[2]


def test_inconclusive_asks_for_clarification():
    """INCONCLUSIVE points at the ambiguity."""
    lines = summarize(status="inconclusive", goal="cancel it")
    assert lines[0].startswith("INCONCLUSIVE")
    assert "Clarify" in lines[2]


def test_failed_names_failure_type():
    """FAILED carries the failure type."""
    lines = summarize(
        status="failed",
        goal="replace the laptop",
        failure={"type": "browser_crashed"},
        error="browser_crashed: tab gone",
    )
    assert lines[0].startswith("FAILED")
    assert "browser_crashed" in lines[1]


def test_llm_draft_changes_nothing():
    """Mutation test: prose anywhere in the facts leaves the summary identical."""
    drafty = _facts(with_draft=True)
    drafty.pop("llm_draft")
    assert summarize(**drafty) == summarize(**_facts())
