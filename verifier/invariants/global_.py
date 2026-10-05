"""Global invariant: nothing changed outside the allowed-effects set.

Runs for every contract, whatever its effects: no removed rows, no added
rows beyond one per contracted effect, no touched customers/orders/items,
and ticket edits limited to status moves (plus version bumps the backend
writes alongside them). Whole-table counts back the scoped reads, so an
insert outside the scope still fails.
"""

from typing import Any

from verifier.readers.scope import COLLECTIONS
from verifier.verdict import check

EFFECT_TABLE = {
    "replacement.create": "replacements",
    "refund.create": "refunds",
    "ticket.note": "ticket_notes",
    "ticket.reply": "ticket_notes",
}

TICKET_ALLOWED_FIELDS = {"status", "version"}


def check_invariant(
    contract: dict[str, Any], diff: dict[str, Any], after: dict[str, Any]
) -> list[dict[str, Any]]:
    """Global outcomes: containment of the whole state change."""
    effects = contract.get("effects", [])
    allowed_adds: dict[str, int] = {}
    for effect in effects:
        table = EFFECT_TABLE.get(effect.get("effect"), "")
        if table:
            allowed_adds[table] = allowed_adds.get(table, 0) + 1
    return [
        _no_removed(diff),
        _added_within_allowance(diff, allowed_adds),
        _untouched_core(diff),
        _ticket_fields(diff, allowed_adds),
        _counts_match(diff, allowed_adds),
    ]


def _no_removed(diff: dict[str, Any]) -> dict[str, Any]:
    """No row disappeared from any scoped collection."""
    removed = {name: len(diff["collections"][name]["removed"]) for name in COLLECTIONS}
    bad = {name: n for name, n in removed.items() if n}
    return check(
        "global.no_removed",
        not bad,
        "no rows removed" if not bad else f"removed rows: {bad}",
    )


def _added_within_allowance(diff: dict[str, Any], allowed_adds: dict[str, int]) -> dict[str, Any]:
    """Added rows match the contracted effects, collection by collection."""
    bad = {}
    for name in COLLECTIONS:
        got = len(diff["collections"][name]["added"])
        want = allowed_adds.get(name, 0)
        if got != want:
            bad[name] = f"added {got}, allowed {want}"
    return check(
        "global.added_within_allowance",
        not bad,
        "adds match effects" if not bad else f"unexpected adds: {bad}",
    )


def _untouched_core(diff: dict[str, Any]) -> dict[str, Any]:
    """Customers, orders, and order items never change in a run."""
    bad = {}
    for name in ("customers", "orders", "order_items"):
        changed = len(diff["collections"][name]["changed"])
        if changed:
            bad[name] = f"changed {changed}"
    return check(
        "global.untouched_core",
        not bad,
        "core entities untouched" if not bad else f"touched core: {bad}",
    )


def _ticket_fields(diff: dict[str, Any], allowed_adds: dict[str, int]) -> dict[str, Any]:
    """Ticket edits are status moves (and version bumps) only."""
    bad = []
    for entry in diff["collections"]["tickets"]["changed"]:
        extra = set(entry["fields"]) - TICKET_ALLOWED_FIELDS
        if extra:
            bad.append(f"{entry['id']}: {sorted(extra)}")
    return check(
        "global.ticket_fields",
        not bad,
        "ticket edits are status moves" if not bad else f"ticket field edits: {bad}",
    )


def _counts_match(diff: dict[str, Any], allowed_adds: dict[str, int]) -> dict[str, Any]:
    """Whole-table count deltas equal the allowed adds (scope-external writes fail)."""
    before = diff["counts"]["before"]
    after = diff["counts"]["after"]
    bad = {}
    for name in COLLECTIONS:
        delta = after.get(name, 0) - before.get(name, 0)
        want = allowed_adds.get(name, 0)
        if name == "tickets":
            want = 0
        if delta != want:
            bad[name] = f"count delta {delta}, allowed {want}"
    return check(
        "global.counts_match",
        not bad,
        "table counts match effects" if not bad else f"count drift: {bad}",
    )
