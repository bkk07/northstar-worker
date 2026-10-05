"""Execution dispatch: every registered tool reaches its gateway call."""

import pytest

from agent.services.execution_service import ExecutionError, ExecutionService


class _StubGateway:
    """Record calls; succeed with tool-shaped payloads (no servers)."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def _call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name == "browser_submit":
                return {
                    "ok": True,
                    "status": 201,
                    "effect": "replacement.create",
                    "mutation_key": kwargs.get("mutation_key", args[2]),
                }
            if name.startswith("browser_"):
                return {"url": "http://x/", "refs": {}}
            return {"items": []}

        return _call


def _service(gateway=None):
    gateway = gateway or _StubGateway()
    service = ExecutionService.__new__(ExecutionService)
    service._gateway = gateway
    return service, gateway


@pytest.mark.parametrize(
    "tool,params",
    [
        ("search_customer", {"q": "ada"}),
        ("get_customer", {"customer_id": "c"}),
        ("search_order", {"customer_id": "c"}),
        ("get_order", {"order_id": "o"}),
        ("get_ticket", {"ticket_id": "t"}),
        ("get_policy", {"rule_key": "k"}),
        ("api_get", {"path": "/api/read/x"}),
        ("inspect_state", {"kind": "k", "key": "v"}),
        ("browser_open", {}),
        ("browser_navigate", {"route": "/ops"}),
        ("browser_observe", {}),
        ("browser_click", {"ref": "e1"}),
        ("browser_fill", {"ref": "e1", "value": "x"}),
        ("browser_back", {}),
        ("browser_screenshot", {}),
    ],
)
def test_each_tool_dispatches(tool, params):
    """Every registered tool maps to exactly its gateway call."""
    service, gateway = _service()
    payload = service._dispatch("task-1", tool, dict(params), "key-1")
    assert gateway.calls and gateway.calls[-1][0] == tool
    assert isinstance(payload, dict)


def test_submit_carries_key_token_and_params():
    """The commit carries the journaled key and the policy token."""
    service, gateway = _service()
    service._dispatch(
        "task-1",
        "browser_submit",
        {"ref": "e9", "token": "tok", "effect": "replacement.create"},
        "key-9",
    )
    name, args, _ = gateway.calls[-1]
    assert name == "browser_submit"
    assert args[1] == "e9" and args[2] == "key-9" and args[3] == "tok"


def test_unknown_tool_raises_without_journal():
    """Unregistered tools fail before any journal row exists."""
    service, _ = _service()
    with pytest.raises(ExecutionError, match="unknown tool"):
        service.execute(
            "t", "00000000-0000-0000-0000-000000000000", {"tool": "delete_everything", "params": {}}
        )


class _NullJournal:
    """Journal double: hands out handles, records finishes (no DB)."""

    def start_action(self, *args, **kwargs):
        from uuid import UUID

        from agent.runtime.journal import StartedAction

        _ = (args, kwargs)
        return StartedAction(
            action_id=UUID("00000000-0000-0000-0000-000000000001"),
            seq=0,
            mutation_key="k",
        )

    def begin_attempt(self, action_id):
        from uuid import UUID

        from agent.runtime.journal import AttemptHandle

        return AttemptHandle(attempt_id=UUID("00000000-0000-0000-0000-000000000002"), attempt_no=1)

    def end_attempt(self, *args, **kwargs):
        _ = (args, kwargs)

    def finish_action(self, *args, **kwargs):
        _ = (args, kwargs)


def test_missing_session_opens_and_retries_once():
    """First browser touch opens the session (observe-before-open works)."""
    service, _ = _service()
    calls = {"observe": 0, "opened": 0}

    class _Sessionless:
        def browser_observe(self, task_id):
            calls["observe"] += 1
            if calls["observe"] == 1:
                raise RuntimeError(f"no session {task_id!r}")
            return {"url": "http://x/ops", "refs": {}}

        def browser_open(self, task_id, target="ops", headless=True):
            calls["opened"] += 1
            _ = (target, headless)
            return {"url": "http://x/ops", "refs": {}}

    service._gateway = _Sessionless()
    service._journal = _NullJournal()
    result = service.execute(
        "t", "00000000-0000-0000-0000-000000000000", {"tool": "browser_observe", "params": {}}
    )
    assert result.ok is True
    assert (calls["observe"], calls["opened"]) == (2, 1)
