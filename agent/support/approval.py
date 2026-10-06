"""Approval policy: when the agent must pause for a human (spec Phase 15).

Pure function, so the matrix is unit-testable and the Phase 9 HITL UI can
preview the reason. High-value refunds pause; low-confidence verdicts
pause; explicit human requests pause. Everything else auto-executes.
"""

HIGH_VALUE_REFUND_PAISE = 500_000  # ₹5,000 auto-approve cap
LOW_CONFIDENCE = 0.6


def needs_approval(
    *,
    action_type: str | None,
    amount_paise: int = 0,
    confidence: float = 1.0,
    human_requested: bool = False,
) -> tuple[bool, str]:
    """(required, reason) for a proposed action."""
    if human_requested:
        return True, "customer asked for a human"
    if confidence < LOW_CONFIDENCE:
        return True, f"low classification confidence ({confidence:.2f})"
    if action_type == "REFUND" and amount_paise >= HIGH_VALUE_REFUND_PAISE:
        return True, f"refund above auto-approve cap (₹{HIGH_VALUE_REFUND_PAISE // 100:,})"
    return False, ""
