"""JSON structured logging with secret scrubbing.

Phase 1: single StreamHandler emitting one JSON object per line.
Secrets (tokens, keys, passwords, cookies) are redacted before emission.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

_SECRET_KEY_PARTS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "passwd",
    "authorization",
    "cookie",
    "set-cookie",
    "client_secret",
)

# Matches `"password": "value"`, `password=value`, `Authorization: Bearer xyz`.
_JSON_VALUE = re.compile(
    r'(?i)("([^"]*(?:api[_-]?key|token|secret|password|passwd|authorization|cookie)[^"]*)"\s*:\s*")[^"]*(")',
)
_KV_VALUE = re.compile(
    r"(?i)((?:api[_-]?key|token|secret|password|passwd|authorization|cookie)[=:]\s*[\"']?)([^\s,;\"']+)",
)
_BEARER_VALUE = re.compile(r"(?i)(Bearer\s+)([A-Za-z0-9._\-~+/=]+)")


REDACTED = "***REDACTED***"


def scrub_secrets(text: str) -> str:
    """Redact secret-looking values from a log string."""
    # Bearer first so `Authorization: Bearer <token>` redacts the token
    # before the generic key=value pattern consumes the `Bearer` word.
    scrubbed = _JSON_VALUE.sub(r"\1" + REDACTED + r"\3", text)
    scrubbed = _BEARER_VALUE.sub(r"\1" + REDACTED, scrubbed)
    scrubbed = _KV_VALUE.sub(r"\1" + REDACTED, scrubbed)
    return scrubbed


class JsonFormatter(logging.Formatter):
    """Emit `record` as a single JSON line with scrubbed message."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": scrub_secrets(record.getMessage()),
        }
        # Attach structured extras without reserved LogRecord attrs.
        reserved = set(
            logging.makeLogRecord({}).__dict__.keys()
        ) | {"message", "msg", "args"}
        for key, value in record.__dict__.items():
            if key not in reserved:
                try:
                    json.dumps(value)
                    payload[key] = value
                except (TypeError, ValueError):
                    payload[key] = str(value)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger once with the JSON handler (idempotent)."""
    root = logging.getLogger()
    if any(isinstance(h, logging.StreamHandler) and isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        root.setLevel(level.upper())
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    """Return a module logger (call `configure_logging` once at startup)."""
    return logging.getLogger(name)
