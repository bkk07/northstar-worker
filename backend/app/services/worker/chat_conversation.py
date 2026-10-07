"""Conversational fallback for open chat messages (no command recognized).

Deterministic command routing stays exactly as it is — this only handles
`unknown` messages (greetings, small talk, free-form asks). The model answers
naturally within its real abilities; it can never mutate anything (approvals
stay button-only, facts come from tools, not memory). Model disabled or any
failure returns None so the caller falls back to the help draft.
"""

from agent.llm.client import LLMError, MercuryClient
from app.services.worker.chat_narrator import TIMEOUT_S, _build_client

SYSTEM = (
    "You are the Northstar support console assistant, chatting with a human "
    "support agent. Be warm, concise, and human (max 80 words). Your real "
    "abilities: run ticket work when given a ticket code (“solve ticket "
    "TCK-…”), report ticket / order / product / policy info when given a "
    "code, list open tickets, show pending approvals. You CANNOT approve or "
    "reject anything (Approve / Reject buttons only) and you must never "
    "invent ticket codes, order codes, amounts, or statuses, nor claim you "
    "did something you didn't. If they greet you, greet back briefly and "
    "offer help. If you can't tell what they want, ask one clarifying "
    "question instead of dumping a menu."
)


def converse(message: str) -> str | None:
    """Natural reply for an open message, or None to use the help draft."""
    try:
        client: MercuryClient | None = _build_client()
    except LLMError:
        return None
    if client is None:
        return None
    try:
        text = client.complete(SYSTEM, f"Support agent said: {message}", timeout_s=TIMEOUT_S)
        return text.strip() or None
    except LLMError:
        return None
    finally:
        client.close()
