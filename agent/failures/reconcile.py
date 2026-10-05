"""Reconciliation: compare a probe hit to the locked contract.

- Hit matches the contract's expected effect → RECONCILED_EXISTING:
  adopt the row, never resubmit.
- Hit belongs to something else → MISMATCH: INCONCLUSIVE for a human.
- Nothing found → ABSENT: exactly one retry with the same key.
"""

from agent.contract.models import Contract

RECONCILED = "reconciled_existing"
MISMATCH = "mismatch"
ABSENT = "absent"


def reconcile_hit(hit, contract: Contract, action: dict) -> tuple[str, str]:
    """Verdict + detail for one probe hit against the contract."""
    params = action.get("params", {})
    effect = params.get("effect", "")
    expected = next((e for e in contract.effects if e.effect == effect), None)
    if expected is None:
        return MISMATCH, f"submit effect {effect!r} outside contract scope"
    for key, wanted in expected.params.items():
        if key in ("order_id", "ticket_id", "customer_id", "order_item_id", "amount_paise"):
            if str(params.get(key, "")) != str(wanted):
                return MISMATCH, f"binding {key} differs from contract"
    kind_ok = (effect == "replacement.create" and hit.kind in ("", "replacement")) or (
        effect == "refund.create" and hit.kind in ("", "refund")
    )
    if not kind_ok and hit.kind:
        return MISMATCH, f"probe kind {hit.kind!r} is not {effect!r}"
    return RECONCILED, f"adopted {hit.kind or effect} {hit.entity_id} via {hit.via}"
