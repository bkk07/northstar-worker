"""Chat run driver retry: transient LLM blips retry, hard errors park fast."""

import pytest

from agent.llm.client import LLMError, is_transient_error
from app.services.worker import chat_runner


def test_transient_predicate() -> None:
    assert is_transient_error(LLMError("HTTP 503: overloaded"))
    assert is_transient_error(LLMError("HTTP 429: slow down"))
    assert is_transient_error(LLMError("transport error: reset"))
    assert not is_transient_error(LLMError("HTTP 401: bad key"))
    assert not is_transient_error(ValueError("boom"))


def test_drive_retries_transient_then_succeeds(monkeypatch) -> None:
    calls: list[str] = []

    def flaky(task_id: str, task_text: str) -> None:
        calls.append(task_id)
        if len(calls) < 3:
            raise LLMError("HTTP 503: overloaded")

    monkeypatch.setattr(chat_runner, "_drive", flaky)
    monkeypatch.setattr(chat_runner.time, "sleep", lambda s: None)
    chat_runner._drive_with_retry("t1", "text")
    assert calls == ["t1", "t1", "t1"]


def test_drive_gives_up_after_attempts(monkeypatch) -> None:
    calls: list[str] = []

    def always_503(task_id: str, task_text: str) -> None:
        calls.append(task_id)
        raise LLMError("HTTP 503: overloaded")

    monkeypatch.setattr(chat_runner, "_drive", always_503)
    monkeypatch.setattr(chat_runner.time, "sleep", lambda s: None)
    with pytest.raises(LLMError):
        chat_runner._drive_with_retry("t1", "text")
    assert len(calls) == chat_runner.DRIVE_ATTEMPTS


def test_drive_does_not_retry_hard_errors(monkeypatch) -> None:
    calls: list[str] = []

    def hard_fail(task_id: str, task_text: str) -> None:
        calls.append(task_id)
        raise LLMError("HTTP 401: bad key")

    monkeypatch.setattr(chat_runner, "_drive", hard_fail)
    monkeypatch.setattr(
        chat_runner.time, "sleep", lambda s: (_ for _ in ()).throw(AssertionError("no sleep"))
    )
    with pytest.raises(LLMError):
        chat_runner._drive_with_retry("t1", "text")
    assert calls == ["t1"]
