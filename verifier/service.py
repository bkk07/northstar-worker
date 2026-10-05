"""Verification service: contract plus snapshots to a verdict.

Inputs are plain data only: the contract's `ExpectedEffects` and the
before/after snapshots. LLM text, UI banners, and agent evidence are
never read. Unknown effects and empty effect lists fail closed; a
missing before-snapshot is INCONCLUSIVE, never a guess.
"""

from typing import Any

from verifier.diff import diff_snapshots
from verifier.invariants import global_, refund, replacement, ticket
from verifier.verdict import FAILED, INCONCLUSIVE, VERIFIED, check, result

KNOWN_EFFECTS = (
    "replacement.create",
    "refund.create",
    "ticket.note",
    "ticket.status",
    "ticket.reply",
)


def verify_contract(
    contract: dict[str, Any], before: dict[str, Any] | None, after: dict[str, Any]
) -> dict[str, Any]:
    """Run per-effect invariants plus the global invariant to a verdict."""
    if not before:
        return result(
            INCONCLUSIVE,
            [check("snapshot.present", False, "missing before-snapshot")],
            {},
        )
    diff = diff_snapshots(before, after)
    effects = contract.get("effects", []) if contract else []
    invariants = []
    unknown = [e.get("effect") for e in effects if e.get("effect") not in KNOWN_EFFECTS]
    if unknown:
        invariants.append(check("effect.known", False, f"effects outside registry: {unknown}"))
    if not effects:
        invariants.append(check("effect.present", False, "contract has no effects"))
    names = {e.get("effect") for e in effects}
    if "replacement.create" in names:
        invariants.extend(replacement.check_invariant(contract, diff, after))
    if "refund.create" in names:
        invariants.extend(refund.check_invariant(contract, diff, after))
    if names & {"ticket.note", "ticket.status", "ticket.reply"}:
        invariants.extend(ticket.check_invariant(contract, diff, after))
    invariants.extend(global_.check_invariant(contract, diff, after))
    verdict = VERIFIED if all(i["passed"] for i in invariants) else FAILED
    return result(verdict, invariants, diff)
