"""Replacement invariant: exactly one new active replacement per effect.

Proves the `replacement.create` effect against the diff and after-state:
one added row for the item, correct customer/order/ticket linkage, and
`pending` status. Duplicates and mislinked rows fail, even when a UI
banner claims success (the verifier never reads banners).
"""

from typing import Any

from verifier.verdict import check

ACTIVE = ("pending", "shipped")


def check_invariant(
    contract: dict[str, Any], diff: dict[str, Any], after: dict[str, Any]
) -> list[dict[str, Any]]:
    """Replacement outcomes for every `replacement.create` effect."""
    results = []
    added = diff["collections"]["replacements"]["added"]
    for effect in contract.get("effects", []):
        if effect.get("effect") != "replacement.create":
            continue
        params = effect.get("params", {})
        item_id = str(params.get("order_item_id", ""))
        matches = [row for row in added if str(row.get("order_item_id")) == item_id]
        if len(matches) != 1:
            results.append(
                check(
                    "replacement.exactly_one",
                    False,
                    f"item {item_id}: expected 1 new replacement, found {len(matches)}",
                )
            )
            continue
        row = matches[0]
        results.append(
            check(
                "replacement.exactly_one",
                True,
                f"item {item_id}: one new replacement {row.get('id')}",
            )
        )
        results.append(_links(row, params, contract))
        results.append(_status(row))
    return results


def _links(row: dict[str, Any], params: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    """Row linkage matches the contract's order, item, ticket, customer."""
    expected = {
        "order_id": str(params.get("order_id", "")),
        "order_item_id": str(params.get("order_item_id", "")),
        "ticket_id": str(params.get("ticket_id", "")),
        "customer_id": str(contract.get("customer_id") or ""),
    }
    bad = [key for key, want in expected.items() if want and str(row.get(key)) != want]
    return check(
        "replacement.links",
        not bad,
        "links match" if not bad else f"mismatched links: {', '.join(bad)}",
    )


def _status(row: dict[str, Any]) -> dict[str, Any]:
    """New replacements start `pending`."""
    ok = row.get("status") == "pending"
    return check(
        "replacement.status",
        ok,
        "status pending" if ok else f"status is {row.get('status')!r}, want 'pending'",
    )
