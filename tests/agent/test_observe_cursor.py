"""Observe node: cursor advances on success (deterministic plan progress)."""

from agent.nodes import observe as observe_node
from agent.runtime import wiring


class _Success:
    def observe(self, task_id, run_id, action, result):
        _ = (task_id, run_id, action, result)
        return type("V", (), {"status": "success", "observation": {"tool": "x", "ok": True}})()


class _Done:
    def observe(self, task_id, run_id, action, result):
        _ = (task_id, run_id, action, result)
        return type("V", (), {"status": "effects_done", "observation": {}})()


def _state(**overrides):
    base = {
        "task_id": "t",
        "run_id": "r",
        "plan": [{"step": "a"}, {"step": "b"}],
        "cursor": 0,
        "last_action": {"tool": "browser_observe", "params": {}, "result": {"ok": True}},
    }
    base.update(overrides)
    return base


def test_success_advances_cursor(monkeypatch):
    """Reads move the plan brief forward (decide sees fresh context)."""
    monkeypatch.setattr(wiring, "observation_service", lambda: _Success())
    delta = observe_node.observe(_state())
    assert delta["cursor"] == 1
    assert delta["observation_status"] == "success"


def test_cursor_caps_at_plan_end(monkeypatch):
    """Cursor never overruns the plan (decide slices safely)."""
    monkeypatch.setattr(wiring, "observation_service", lambda: _Success())
    delta = observe_node.observe(_state(cursor=2))
    assert delta["cursor"] == 2


def test_effects_done_leaves_cursor(monkeypatch):
    """Commits route to verify; the cursor is irrelevant after that."""
    monkeypatch.setattr(wiring, "observation_service", lambda: _Done())
    delta = observe_node.observe(_state(cursor=1))
    assert delta["observation_status"] == "effects_done"
    assert "cursor" not in delta
