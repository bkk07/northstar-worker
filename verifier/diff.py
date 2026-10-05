"""State diff: before/after snapshots to added/removed/changed rows.

The diff is plain data. `changed` entries carry only the fields that
moved (`{field: [before, after]}`), so invariants can allow benign
columns (ticket version bumps) while failing on anything else.
"""

from typing import Any

from verifier.readers.scope import COLLECTIONS


def diff_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Diff two snapshots into per-collection row changes and counts."""
    collections = {}
    for name in COLLECTIONS:
        collections[name] = _diff_collection(before.get(name, []), after.get(name, []))
    return {
        "collections": collections,
        "counts": {
            "before": dict(before.get("counts", {})),
            "after": dict(after.get("counts", {})),
        },
    }


def _diff_collection(
    before_rows: list[dict[str, Any]], after_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Added, removed, and field-level changed rows for one collection."""
    before_by_id = {str(row.get("id")): row for row in before_rows}
    after_by_id = {str(row.get("id")): row for row in after_rows}
    added = [row for key, row in after_by_id.items() if key not in before_by_id]
    removed = [row for key, row in before_by_id.items() if key not in after_by_id]
    changed = []
    for key in before_by_id.keys() & after_by_id.keys():
        fields = _changed_fields(before_by_id[key], after_by_id[key])
        if fields:
            changed.append({"id": key, "fields": fields})
    return {"added": added, "removed": removed, "changed": changed}


def _changed_fields(before_row: dict[str, Any], after_row: dict[str, Any]) -> dict[str, Any]:
    """Fields whose values moved, `{field: [before, after]}`."""
    fields = {}
    for key in before_row.keys() | after_row.keys():
        old, new = before_row.get(key), after_row.get(key)
        if old != new:
            fields[key] = [old, new]
    return fields
