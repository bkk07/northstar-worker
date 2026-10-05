"""Mercury client: retries, errors, and one live smoke test (Phase 12).

Unit tests fake the transport; only the `llm`-marked smoke test touches
the real API, and only with an explicit opt-in (`RUN_LLM_TESTS=1` plus a
key), so the default suite stays hermetic.
"""

import json
import os

import pytest
from pydantic import BaseModel, Field

from agent.llm.client import (
    LLMError,
    MalformedResponseError,
    MercuryClient,
    MercuryConfig,
    config_from_env,
)


class EchoSchema(BaseModel):
    """Trivial schema for retry tests and the live smoke test."""

    word: str = Field(min_length=1)
    n: int = Field(ge=0)


class _FakeResponse:
    """Minimal httpx response double."""

    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.text = body if isinstance(body, str) else json.dumps(body)

    def json(self):
        """Parse the body (mirrors httpx raising on bad JSON)."""
        if isinstance(self._body, str):
            return json.loads(self._body)
        return self._body


class _FakeHttp:
    """Queued transport double (plays responses in order)."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def post(self, path, json=None):
        """Record the call and play the next queued response."""
        self.calls += 1
        self.request_path = path
        self.request_json = json
        played = self._responses.pop(0)
        if isinstance(played, Exception):
            raise played
        return played


def _client(responses, **overrides):
    config = MercuryConfig(api_key="test-key", **overrides)
    client = MercuryClient(config)
    client._http = _FakeHttp(responses)
    return client


def _completion(content):
    return {"choices": [{"message": {"content": content}}]}


def test_config_requires_key():
    """Missing INCEPTION_API_KEY fails fast with a clear error."""
    with pytest.raises(LLMError, match="INCEPTION_API_KEY"):
        config_from_env({})
    config = config_from_env({"INCEPTION_API_KEY": "k", "INCEPTION_MODEL": "mercury-2.5"})
    assert config.model == "mercury-2.5"
    assert config.base_url.startswith("https://")


def test_temperature_zero_and_schema_sent():
    """Every call pins temperature 0 with a JSON-schema response format."""
    client = _client([_FakeResponse(200, _completion('{"word": "hi", "n": 1}'))])
    result = client.propose(EchoSchema, "sys", "user")
    assert result.word == "hi"
    payload = client._http.request_json
    assert payload["temperature"] == 0
    assert payload["model"] == "mercury-2.5"
    assert payload["response_format"]["type"] == "json_schema"
    assert client._http.request_path == "/chat/completions"


def test_malformed_json_retries_then_succeeds():
    """Garbage first reply is repaired with a nudge, not trusted."""
    client = _client(
        [
            _FakeResponse(200, _completion("Sure! Here you go...")),
            _FakeResponse(200, _completion('{"word": "ok", "n": 2}')),
        ]
    )
    result = client.propose(EchoSchema, "sys", "user")
    assert (result.word, result.n) == ("ok", 2)
    assert client._http.calls == 2


def test_schema_mismatch_retries_then_succeeds():
    """Valid JSON with the wrong shape is a retry, not a proposal."""
    client = _client(
        [
            _FakeResponse(200, _completion('{"word": "x"}')),
            _FakeResponse(200, _completion('{"word": "y", "n": 3}')),
        ]
    )
    assert client.propose(EchoSchema, "sys", "user").n == 3


def test_exhausted_retries_raise():
    """Bounded retries: garbage forever becomes MalformedResponseError."""
    client = _client([_FakeResponse(200, _completion("nope"))] * 3, max_retries=2)
    with pytest.raises(MalformedResponseError):
        client.propose(EchoSchema, "sys", "user")
    assert client._http.calls == 3


def test_http_error_raises_immediately():
    """Auth failures raise at once (retries never help a bad key)."""
    client = _client([_FakeResponse(401, "bad key")])
    with pytest.raises(LLMError, match="HTTP 401"):
        client.propose(EchoSchema, "sys", "user")


def test_transport_blip_retries_then_succeeds():
    """Flaky reads retry inside the call (runs survive API blips)."""
    import httpx

    client = _client(
        [httpx.ReadTimeout("slow"), _FakeResponse(200, _completion('{"word": "ok", "n": 1}'))],
        max_retries=2,
    )
    assert client.propose(EchoSchema, "sys", "user").word == "ok"
    assert client._http.calls == 2


@pytest.mark.llm
def test_live_mercury_smoke():
    """Trivial live call (opt-in: RUN_LLM_TESTS=1 with INCEPTION_API_KEY)."""
    if os.environ.get("RUN_LLM_TESTS") != "1" or not os.environ.get("INCEPTION_API_KEY"):
        pytest.skip("live LLM test needs RUN_LLM_TESTS=1 and INCEPTION_API_KEY")
    client = MercuryClient(config_from_env())
    try:
        result = client.propose(
            EchoSchema, "Reply with the exact object.", '{"word": "ping", "n": 2}'
        )
    finally:
        client.close()
    assert result.word and result.n >= 0
