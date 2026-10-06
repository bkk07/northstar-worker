"""Chat narrator: model phrasing over deterministic drafts (fakes only)."""

from agent.llm.client import LLMError
from app.services.worker.chat_narrator import narrate


class _FakeClient:
    """Stand-in model client (records close, never touches the network)."""

    def __init__(self, text: str | None) -> None:
        self._text = text
        self.closed = False

    def complete(self, system: str, user: str, timeout_s: float | None = None) -> str:
        assert "TCK-102" in user  # the draft grounds the prompt
        if self._text is None:
            raise LLMError("transport error: down")
        return self._text

    def close(self) -> None:
        self.closed = True


def test_no_client_keeps_draft():
    """Unconfigured model returns the deterministic draft untouched."""
    assert narrate("hi", "draft", build_client=lambda: None) == "draft"


def test_client_failure_keeps_draft():
    """Factory blowups fall back to the draft (never an error)."""
    def _boom():
        raise LLMError("INCEPTION_API_KEY is not set")

    assert narrate("hi", "draft", build_client=_boom) == "draft"


def test_model_rephrases_and_closes():
    """Healthy model rephrases; the client is always released."""
    client = _FakeClient("TCK-102 is open and ready.")
    assert (
        narrate("status of TCK-102?", "TCK-102 is open.", build_client=lambda: client)
        == "TCK-102 is open and ready."
    )
    assert client.closed


def test_model_error_keeps_draft():
    """Mid-call model failures fall back to the draft."""
    assert (
        narrate("status of TCK-102?", "TCK-102 is open.", build_client=lambda: _FakeClient(None))
        == "TCK-102 is open."
    )
