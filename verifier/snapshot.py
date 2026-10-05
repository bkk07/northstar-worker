"""Snapshots: canonical before/after state for the verifier.

A snapshot is plain JSON-serializable data: scoped collections sorted by
row id, plus whole-table counts. Sorting and scalar canonicalization make
snapshots comparable across sessions and roles.
"""

from typing import Any

from sqlalchemy.orm import Session

from verifier.readers.scope import COLLECTIONS, read_scope


def take_snapshot(session: Session, scope: dict[str, Any]) -> dict[str, Any]:
    """Read the scope and return a canonical snapshot dict."""
    data = read_scope(session, scope or {})
    return {
        name: sorted(data.get(name, []), key=_row_key) for name in COLLECTIONS if name in data
    } | {"counts": dict(data.get("counts", {}))}


def _row_key(row: dict[str, Any]) -> str:
    """Stable sort key: the row id, stringified."""
    return str(row.get("id", ""))
