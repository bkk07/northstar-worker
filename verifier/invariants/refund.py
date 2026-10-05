"""Refund invariant: exactly one new refund with the contracted amount.

Proves the `refund.create` effect: one added row for the order/ticket,
amount equal to the contract (paise), correct linkage, and total refunds
on the order within what was paid.
"""

from typing import Any

from verifier.verdict import check


def check_invariant(
    contract: dict[str, Any], diff: dict[str, Any], after: dict[str, Any]
) -> list[dict[str, Any]]:
    """Refund outcomes for every `refund.create` effect."""
    results = []
    added = diff["collections"]["refunds"]["added"]
    for effect in contract.get("effects", []):
        if effect.get("effect") != "refund.create":
            continue
        params = effect.get("params", {})
        order_id = str(params.get("order_id", ""))
        ticket_id = str(params.get("ticket_id", ""))
        matches = [
            row
            for row in added
            if str(row.get("order_id")) == order_id and str(row.get("ticket_id")) == ticket_id
        ]
        if len(matches) != 1:
            results.append(
                check(
                    "refund.exactly_one",
                    False,
                    f"order {order_id}: expected 1 new refund, found {len(matches)}",
                )
            )
            continue
        row = matches[0]
        results.append(
            check(
                "refund.exactly_one",
                True,
                f"order {order_id}: one new refund {row.get('id')}",
            )
        )
        results.append(_amount(row, params))
        results.append(_links(row, params, contract))
        results.append(_within_paid(row, after))
    return results


def _amount(row: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    """Refund amount equals the contract amount (integer paise)."""
    want = params.get("amount_paise")
    ok = row.get("amount_paise") == want
    return check(
        "refund.amount",
        ok,
        f"amount {row.get('amount_paise')}"
        if ok
        else (f"amount {row.get('amount_paise')!r}, want {want!r}"),
    )


def _links(row: dict[str, Any], params: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    """Row linkage matches the contract's order, ticket, customer."""
    expected = {
        "order_id": str(params.get("order_id", "")),
        "ticket_id": str(params.get("ticket_id", "")),
        "customer_id": str(contract.get("customer_id") or ""),
    }
    bad = [key for key, want in expected.items() if want and str(row.get(key)) != want]
    return check(
        "refund.links",
        not bad,
        "links match" if not bad else f"mismatched links: {', '.join(bad)}",
    )


def _within_paid(row: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Total non-cancelled refunds on the order stay within paid."""
    order_id = str(row.get("order_id"))
    orders = [o for o in after.get("orders", []) if str(o.get("id")) == order_id]
    if not orders:
        return check("refund.within_paid", False, f"order {order_id} not in scope")
    paid = orders[0].get("paid_paise") or 0
    total = sum(
        r.get("amount_paise") or 0
        for r in after.get("refunds", [])
        if str(r.get("order_id")) == order_id and r.get("status") != "cancelled"
    )
    ok = total <= paid
    return check(
        "refund.within_paid",
        ok,
        f"refunded {total} of paid {paid}" if ok else (f"refunded {total} exceeds paid {paid}"),
    )
