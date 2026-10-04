"""VerifierPort: the agent-side contract for independent verification.

The verifier reads real DB state with its own role and imports nothing
from the agent; this Protocol is the only seam. The `verify` node calls
it, then routes on the plain-data verdict (Phase 21 wires the adapter).
"""

from typing import Protocol, TypedDict


class VerificationResult(TypedDict, total=False):
    """Plain-data verdict: never LLM text, never UI banners."""

    verdict: str
    invariants: list[dict]
    diff: dict


class VerifierPort(Protocol):
    """Independent proof of outcome for one run."""

    def verify(self, contract: dict, run_id: str) -> VerificationResult:
        """Snapshots, diff, and invariants for the contract's effects."""
        ...
