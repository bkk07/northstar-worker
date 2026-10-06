"""LLM client config: provider retargeting and strict-schema toggle."""

from pydantic import BaseModel

from agent.llm.client import _response_format, config_from_env


class _M(BaseModel):
    answer: str


def _env(**overrides):
    base = {"INCEPTION_API_KEY": "test-key"}
    base.update(overrides)
    return base


def test_strict_schema_default():
    """Strict json_schema mode stays the default (Mercury behavior)."""
    config = config_from_env(_env())
    assert config.strict_schema is True
    assert config.base_url == "https://api.inceptionlabs.ai/v1"
    assert config.model == "mercury-2.5"
    assert _response_format(_M, True)["type"] == "json_schema"


def test_strict_schema_disabled_by_env():
    """`INCEPTION_STRICT_SCHEMA=0` falls back to JSON mode (Groq path)."""
    config = config_from_env(_env(INCEPTION_STRICT_SCHEMA="0"))
    assert config.strict_schema is False
    assert _response_format(_M, False) == {"type": "json_object"}


def test_provider_retarget():
    """Base URL and model retarget the client (provider switch without code)."""
    config = config_from_env(
        _env(
            INCEPTION_BASE_URL="https://api.groq.com/openai/v1",
            INCEPTION_MODEL="openai/gpt-oss-120b",
        )
    )
    assert config.base_url == "https://api.groq.com/openai/v1"
    assert config.model == "openai/gpt-oss-120b"


def test_reasoning_effort_defaults_to_omitted():
    """No effort configured means the parameter stays out of requests."""
    assert config_from_env(_env()).reasoning_effort == ""


def test_reasoning_effort_configured():
    """`INCEPTION_REASONING_EFFORT=minimal` passes through normalized."""
    config = config_from_env(_env(INCEPTION_REASONING_EFFORT=" Minimal "))
    assert config.reasoning_effort == "minimal"
