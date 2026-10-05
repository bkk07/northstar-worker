"""Generalization mechanics: freeze diff, seal helpers, table math."""

from eval.generalization import (
    CORE_DIRS,
    comparison_table,
    core_diff,
    seal_catalog,
    verify_seal,
)


def test_core_unchanged_since_freeze():
    """No core edits since the freeze tag (fixes would list here)."""
    diff = core_diff()
    assert set(diff["per_dir"]) == set(CORE_DIRS)
    assert diff["total"] == 0, diff


def test_seal_helpers_agree():
    """Seal and verify are consistent on the committed held-out file."""
    assert verify_seal()
    assert len(seal_catalog()) == 64


def test_comparison_table_deltas_rates():
    """Seeded vs held-out rows carry both sides and the delta."""
    seeded = {"scenarios": 11, "task_success_rate": 0.5, "avg_tool_calls": 4.0}
    held_out = {"scenarios": 6, "task_success_rate": 0.75, "avg_tool_calls": 3.0}
    rows = {row["metric"]: row for row in comparison_table(seeded, held_out)}
    assert rows["task_success_rate"]["delta"] == 0.25
    assert rows["avg_tool_calls"]["delta"] == -1.0
    assert rows["task_success_rate"]["seeded"] == 0.5
    assert "scenarios" not in rows
