"""Verdicts: the verifier never returns a forced boolean.

VERIFIED means every invariant for the contract's effects plus the
global invariant passed. FAILED names the violated invariants. Missing
snapshots or unreadable data yield INCONCLUSIVE, never a guess.
"""

from typing import Any

VERIFIED = "verified"
FAILED = "failed"
INCONCLUSIVE = "inconclusive"


def result(verdict: str, invariants: list[dict[str, Any]], diff: dict[str, Any]) -> dict[str, Any]:
    """One plain-data verification result for the graph and the journal."""
    return {"verdict": verdict, "invariants": list(invariants), "diff": dict(diff)}


def check(name: str, passed: bool, detail: str = "") -> dict[str, Any]:
    """One invariant outcome: name, boolean, human-readable detail."""
    return {"name": name, "passed": bool(passed), "detail": detail}
