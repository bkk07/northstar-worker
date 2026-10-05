"""Structured logging: every line carries the run context (Phase 24).

`log_event` emits one JSON object per line — `ts`, `component`,
`event`, plus the caller fields (`task_id`, `run_id`, `node`, ...).
Operators grep one field; the audit table stays the system of record.
"""

import datetime
import json
import sys


def log_event(component: str, event: str, **fields) -> None:
    """One JSON line on stdout (structured fields, never free prose)."""
    record = {
        "ts": datetime.datetime.now(datetime.UTC).isoformat(),
        "component": component,
        "event": event,
        **{key: value for key, value in fields.items() if value is not None},
    }
    sys.stdout.write(json.dumps(record, default=str) + "\n")
    sys.stdout.flush()
