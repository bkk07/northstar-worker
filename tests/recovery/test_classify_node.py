"""Classify node: types the failure, bumps the count, audits it."""

from agent.nodes import classify as classify_node


class _FakeAudit:
    def __init__(self):
        self.events = []

    def emit(self, task_id, run_id, node, kind, **kwargs):
        self.events.append({"node": node, "kind": kind, **kwargs})


def _state(**overrides):
    base = {
        "task_id": "t",
        "run_id": "r",
        "last_action": {
            "tool": "get_order",
            "params": {},
            "result": {"ok": False, "error": "connection refused", "error_type": "ConnectionError"},
        },
        "last_observation": {"tool": "get_order", "ok": False, "error": "connection refused"},
    }
    base.update(overrides)
    return base


def test_classify_types_and_counts(monkeypatch):
    """A read transport error is a network_error at count 1."""
    from agent.runtime import wiring

    fake = _FakeAudit()
    monkeypatch.setattr(wiring, "audit_emitter", lambda: fake)
    delta = classify_node.classify(_state())
    assert delta == {"failure": {"type": "network_error", "count": 1}}
    assert fake.events and fake.events[0]["kind"] == "failure.classified"
    assert fake.events[0]["error_type"] == "network_error"


def test_classify_bumps_existing_count(monkeypatch):
    """Retries accumulate (the router bounds them in Phase 18)."""
    from agent.runtime import wiring

    monkeypatch.setattr(wiring, "audit_emitter", lambda: _FakeAudit())
    state = _state(failure={"type": "network_error", "count": 2})
    assert classify_node.classify(state)["failure"]["count"] == 3


def test_classify_write_500_is_unknown(monkeypatch):
    """Commits that fail dirty need probe, never blind retry."""
    from agent.runtime import wiring

    monkeypatch.setattr(wiring, "audit_emitter", lambda: _FakeAudit())
    state = _state(
        last_action={
            "tool": "browser_submit",
            "params": {},
            "result": {
                "ok": False,
                "payload": {"ok": False, "status": 500},
                "error": "",
                "error_type": "",
            },
        },
        last_observation={"tool": "browser_submit", "ok": False},
    )
    assert classify_node.classify(state)["failure"]["type"] == "unknown_outcome"
