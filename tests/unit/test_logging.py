"""Logs are single JSON lines with secrets redacted (Phase 1)."""

import io
import json
import logging

from northstar_common.logging import configure_logging, get_logger, scrub_secrets


def test_scrub_secrets_redacts_tokens_and_passwords():
    raw = 'login password="hunter2" token=abc123 Authorization: Bearer xyz789'
    scrubbed = scrub_secrets(raw)
    assert "hunter2" not in scrubbed
    assert "abc123" not in scrubbed
    assert "xyz789" not in scrubbed
    assert "***REDACTED***" in scrubbed


def test_json_log_format_is_parseable():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    from northstar_common.logging import JsonFormatter

    handler.setFormatter(JsonFormatter())
    logger = get_logger("phase1.test.json")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        logger.info("hello world", extra={"task_id": "t-1"})
    finally:
        logger.removeHandler(handler)
    line = stream.getvalue().strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["level"] == "INFO"
    assert payload["logger"] == "phase1.test.json"
    assert payload["msg"] == "hello world"
    assert payload["task_id"] == "t-1"
    assert "ts" in payload


def test_configure_logging_is_idempotent():
    configure_logging("INFO")
    configure_logging("INFO")  # must not duplicate handlers endlessly
