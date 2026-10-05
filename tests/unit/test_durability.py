"""Phase 20: budgets, resume overlays (pure, no DB)."""

from agent.runtime import budgets
from agent.runtime.resume import fresh_or_resumed, resume_overlay


def test_budgets_default_limits_match_plan():
    """The six enforced bounds equal the §19 config."""
    assert budgets.DEFAULT_LIMITS == {
        "iterations": 40,
        "tool_calls": 60,
        "retries_per_action": 3,
        "total_retries": 10,
        "recovery_attempts": 6,
        "runtime_s": 300,
        "approval_wait_s": 86400,
    }


def test_check_names_first_breach():
    """The first blown bound is reported (BUDGET_EXCEEDED carries it)."""
    assert budgets.check({}) is None
    assert budgets.check({"iterations": 40}) is None
    assert budgets.check({"iterations": 41}) == "iterations"
    assert budgets.check({"runtime_s": 301}) == "runtime_s"


def test_exceeded_reads_state_flag_first():
    """A parked budget flag beats counters (edges fail closed on it)."""
    state = {"budget_exceeded": "tool_calls", "budgets": {"used": {}}}
    assert budgets.exceeded(state) == "tool_calls"
    assert budgets.exceeded({"budgets": {"used": {"tool_calls": 61}}}) == "tool_calls"
    assert budgets.exceeded({"budgets": {"used": {}}}) is None


def test_resume_completed_action_verbatim():
    """Clean checkpoints resume exactly (no reinterpretation)."""
    checkpoint = {"cursor": 2, "plan": [{"step": "x"}]}
    done = {"tool": "browser_observe", "status": "done"}
    assert resume_overlay(checkpoint, done) == checkpoint
    assert resume_overlay(checkpoint, None) == checkpoint


def test_resume_interrupted_write_becomes_unknown():
    """A STARTED write restarts as an unknown outcome (probe follows)."""
    started = {
        "tool": "browser_submit",
        "status": "started",
        "mutation_key": "k",
        "params": {"effect": "refund.create"},
    }
    overlay = resume_overlay({"cursor": 1}, started)
    assert overlay["observation_status"] == "failure"
    assert overlay["last_observation"]["mutated"] is False
    assert overlay["last_observation"]["mutation_key"] == "k"


def test_resume_interrupted_read_reruns():
    """An interrupted read drops its partial observation (safe to redo)."""
    started = {"tool": "get_order", "status": "started", "params": {}}
    overlay = resume_overlay(
        {"cursor": 1, "last_observation": {"partial": True}, "observation_status": "success"},
        started,
    )
    assert "last_observation" not in overlay
    assert "observation_status" not in overlay
    assert overlay["last_action"]["tool"] == "get_order"


def test_fresh_or_resumed_seeds_new_runs():
    """No checkpoint → seed; checkpoint → overlay on the new run's ids."""
    fresh = fresh_or_resumed("t", "r-new", "do x", None, None)
    assert fresh["task_id"] == "t" and fresh["run_id"] == "r-new"
    resumed = fresh_or_resumed(
        "t", "r-new", "do x", {"cursor": 3}, {"tool": "get_order", "status": "done"}
    )
    assert resumed["cursor"] == 3 and resumed["run_id"] == "r-new"
