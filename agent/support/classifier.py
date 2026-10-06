"""Supervisor intent classification (spec Phase 8).

Live path: Groq structured proposal (`IntentClassification`). Mock path
(`llm=None`): the ticket's own category answers directly for the four
action categories (0.9 confidence); otherwise keyword routing with modest
confidence, so low-confidence tickets flow to HITL instead of acting.
"""

from agent.support.schemas import INTENTS, IntentClassification

_CATEGORY_TO_INTENT = {
    "REFUND": "REFUND",
    "REPLACEMENT": "REPLACEMENT",
    "RETURN": "RETURN",
    "CANCELLATION": "CANCELLATION",
}

_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("REFUND", ("refund", "money back", "charged twice", "overcharged")),
    ("REPLACEMENT", ("replacement", "replace", "wrong item", "damaged", "broken", "defective")),
    ("RETURN", ("return", "send back", "pickup", "pick up")),
    ("CANCELLATION", ("cancel", "cancellation", "stop the order")),
    ("ORDER_STATUS", ("where is", "status", "track", "tracking", "when will")),
    ("DELIVERY", ("deliver", "delivery", "late", "delayed", "not arrived", "shipping")),
    ("PAYMENT", ("payment", "pay", "upi", "card", "transaction", "failed to pay")),
)

_CLASSIFY_SYSTEM = (
    "You triage ecommerce support tickets. Reply with ONLY the JSON object "
    '{"intent, confidence, order_id}. Intent is one of: ' + ", ".join(INTENTS) + ". "
    "ORDER_STATUS asks where an order is; DELIVERY complains about lateness; "
    "PAYMENT is about paying; GENERAL_QUERY is anything else."
)


def mock_classify(subject: str, description: str, category: str) -> IntentClassification:
    """Deterministic classifier (no model)."""
    direct = _CATEGORY_TO_INTENT.get((category or "").strip().upper())
    if direct:
        return IntentClassification(intent=direct, confidence=0.9)
    text = f"{subject} {description}".lower()
    for intent, words in _KEYWORDS:
        if any(w in text for w in words):
            return IntentClassification(intent=intent, confidence=0.55)
    return IntentClassification(intent="GENERAL_QUERY", confidence=0.4)


def classify(subject: str, description: str, category: str, llm=None) -> IntentClassification:
    """Classify a ticket (live Groq proposal, or mock when `llm=None`)."""
    if llm is None:
        return mock_classify(subject, description, category)
    user = f"Subject: {subject}\nCategory hint: {category}\nDescription: {description}"
    return llm.propose(IntentClassification, _CLASSIFY_SYSTEM, user)
