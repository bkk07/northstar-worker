"""Snapshot and diff unit tests (pure, no DB)."""

from verifier.diff import diff_snapshots


def _snap(**collections):
    base = {
        "customers": [],
        "orders": [],
        "order_items": [],
        "tickets": [],
        "ticket_notes": [],
        "refunds": [],
        "replacements": [],
    }
    base.update(collections)
    base["counts"] = {name: len(rows) for name, rows in base.items() if name != "counts"}
    return base


def test_diff_detects_added_row():
    before = _snap()
    after = _snap(replacements=[{"id": "r1", "status": "pending"}])
    diff = diff_snapshots(before, after)
    assert [r["id"] for r in diff["collections"]["replacements"]["added"]] == ["r1"]
    assert diff["collections"]["replacements"]["removed"] == []


def test_diff_detects_field_change_only():
    before = _snap(tickets=[{"id": "t1", "status": "open", "version": 1}])
    after = _snap(tickets=[{"id": "t1", "status": "resolved", "version": 2}])
    diff = diff_snapshots(before, after)
    changed = diff["collections"]["tickets"]["changed"]
    assert len(changed) == 1
    assert changed[0]["fields"] == {
        "status": ["open", "resolved"],
        "version": [1, 2],
    }


def test_diff_quiet_on_identical_snapshots():
    snap = _snap(orders=[{"id": "o1", "status": "delivered"}])
    diff = diff_snapshots(snap, snap)
    for collection in diff["collections"].values():
        assert collection == {"added": [], "removed": [], "changed": []}


def test_diff_detects_removed_row():
    before = _snap(refunds=[{"id": "f1", "amount_paise": 100}])
    after = _snap()
    diff = diff_snapshots(before, after)
    removed = diff["collections"]["refunds"]["removed"]
    assert [r["id"] for r in removed] == ["f1"]
