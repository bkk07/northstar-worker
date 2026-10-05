"""Mercury 2.5 client: structured proposals, temperature 0.

Thin wrapper over the OpenAI-compatible Inception endpoint
(`https://api.inceptionlabs.ai/v1/chat/completions`). The client sends a
JSON-schema response format, parses exactly one JSON object, validates it
against the caller's pydantic model, and retries bounded times on
malformed JSON — then raises instead of guessing. HTTP failures raise
immediately: the graph treats them as failures to classify, not retries
(the recovery router owns retry policy in Phase 18).
"""

import json
import os
from dataclasses import dataclass
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from northstar_common.errors import NorthstarError

DEFAULT_BASE_URL = "https://api.inceptionlabs.ai/v1"
DEFAULT_MODEL = "mercury-2.5"
SCHEMA_NAME_LIMIT = 64

T = TypeVar("T", bound=BaseModel)


class LLMError(NorthstarError):
    """The proposal call failed (transport, auth, or server error)."""

    code = "LLM_ERROR"


class MalformedResponseError(LLMError):
    """Exhausted retries without one schema-valid JSON object."""

    code = "LLM_MALFORMED"


@dataclass(frozen=True)
class MercuryConfig:
    """Connection + sampling config (temperature is always 0)."""

    api_key: str
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    timeout_s: float = 30.0
    max_retries: int = 2
    strict_schema: bool = True


def config_from_env(env: dict[str, str] | None = None) -> MercuryConfig:
    """Build config from the documented `INCEPTION_*` variables."""
    source = env if env is not None else os.environ
    api_key = source.get("INCEPTION_API_KEY", "")
    if not api_key:
        raise LLMError("INCEPTION_API_KEY is not set")
    model = source.get("INCEPTION_MODEL", "") or DEFAULT_MODEL
    base_url = source.get("INCEPTION_BASE_URL", "") or DEFAULT_BASE_URL
    timeout = float(source.get("LLM_TIMEOUT_S", "30"))
    retries = int(source.get("LLM_MAX_RETRIES", "2"))
    return MercuryConfig(
        api_key=api_key, model=model, base_url=base_url, timeout_s=timeout, max_retries=retries
    )


def _inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Inline local `$defs` so strict-mode schemas carry no references."""
    defs = schema.pop("$defs", {})
    dumped = json.dumps(schema)

    def replace(node: Any) -> Any:
        if isinstance(node, dict):
            if set(node) == {"$ref"} and node["$ref"].startswith("#/$defs/"):
                return replace(defs[node["$ref"].split("/")[-1]])
            return {key: replace(value) for key, value in node.items()}
        if isinstance(node, list):
            return [replace(item) for item in node]
        return node

    return replace(json.loads(dumped))


def _strict_schema(model_cls: type[BaseModel]) -> dict[str, Any]:
    """Pydantic JSON schema hardened for strict structured outputs."""
    schema = _inline_refs(model_cls.model_json_schema())

    def harden(node: Any) -> Any:
        if isinstance(node, dict):
            node.pop("title", None)
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = sorted(node["properties"])
            return {key: harden(value) for key, value in node.items()}
        if isinstance(node, list):
            return [harden(item) for item in node]
        return node

    return harden(schema)


def _response_format(model_cls: type[BaseModel], strict: bool) -> dict[str, Any]:
    if not strict:
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": model_cls.__name__[:SCHEMA_NAME_LIMIT],
            "strict": True,
            "schema": _strict_schema(model_cls),
        },
    }


class MercuryClient:
    """Structured proposals from Mercury 2.5 (temperature 0, always)."""

    def __init__(self, config: MercuryConfig) -> None:
        self._config = config
        self._http = httpx.Client(
            base_url=config.base_url.rstrip("/"),
            timeout=config.timeout_s,
            headers={"Authorization": f"Bearer {config.api_key}"},
        )

    def close(self) -> None:
        """Release the underlying connection pool."""
        self._http.close()

    def propose(self, model_cls: type[T], system: str, user: str) -> T:
        """One schema-valid proposal (retries transport + malformed JSON)."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        attempts = 1 + max(0, self._config.max_retries)
        last_error = "no attempts made"
        for attempt in range(attempts):
            try:
                content = self._chat(messages, model_cls)
            except LLMError as exc:
                last_error = f"attempt {attempt + 1}: {exc}"
                if not _retryable(exc) or attempt + 1 >= attempts:
                    raise
                continue
            try:
                data = json.loads(content)
            except (TypeError, ValueError) as exc:
                last_error = f"attempt {attempt + 1}: not JSON: {exc}"
                messages = _repair_nudge(messages, last_error)
                continue
            try:
                return model_cls.model_validate(data)
            except ValidationError as exc:
                last_error = f"attempt {attempt + 1}: schema mismatch: {exc.errors()}"
                messages = _repair_nudge(messages, last_error)
                continue
        raise MalformedResponseError(
            f"no schema-valid {model_cls.__name__} after {attempts} attempts ({last_error})"
        )

    def _chat(self, messages: list[dict[str, str]], model_cls: type[BaseModel]) -> str:
        try:
            response = self._http.post(
                "/chat/completions",
                json={
                    "model": self._config.model,
                    "messages": messages,
                    "temperature": 0,
                    "response_format": _response_format(model_cls, self._config.strict_schema),
                },
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"transport error: {exc}") from exc
        if response.status_code >= 400:
            raise LLMError(f"HTTP {response.status_code}: {response.text[:500]}")
        try:
            body = response.json()
            return body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"unreadable chat payload: {exc}") from exc


def _retryable(exc: LLMError) -> bool:
    """Retry transport blips and server-side 5xx/429 (never 4xx/auth)."""
    text = str(exc)
    if text.startswith("transport error"):
        return True
    return any(code in text for code in ("HTTP 429", "HTTP 500", "HTTP 502", "HTTP 503"))


def _repair_nudge(messages: list[dict[str, str]], error: str) -> list[dict[str, str]]:
    """Append a bounded repair request (previous turns are kept)."""
    return messages + [
        {
            "role": "user",
            "content": (
                "Your previous reply was unusable "
                f"({error}). Reply with ONLY the JSON object, no prose."
            ),
        }
    ]
