"""Chat narrator: model-phrased answers over deterministic facts.

Intent parsing, database reads, and side effects stay exactly as they are —
the model only rephrases the drafted reply into a natural answer. The draft
is the ground truth: the prompt forbids inventing codes, amounts, or actions,
and any model failure silently falls back to the draft (never an error).
"""

from collections.abc import Callable
import os

from agent.llm.client import LLMError, MercuryClient, config_from_env

SYSTEM = (
    "You are the Northstar support bot. Rephrase the DRAFT reply into a warm, "
    "concise answer (max 120 words). Rules: keep every ticket code, order code, "
    "SKU, amount, and policy rule key EXACTLY as written; never invent facts, "
    "actions taken, or decisions; never approve, reject, or answer on anyone's "
    "behalf — if the draft says something needs a button, keep that meaning; "
    "reply with ONLY the rephrased answer, no preamble."
)

# Short leash: chat turns must feel instant; the draft is always acceptable.
TIMEOUT_S = float(os.environ.get("CHAT_LLM_TIMEOUT_S", "25"))


def _build_client() -> MercuryClient | None:
    """Model client, or None when disabled/unconfigured (draft path)."""
    if os.environ.get("CHAT_USE_MODEL", "1").strip().lower() in ("0", "false", "no"):
        return None
    try:
        return MercuryClient(config_from_env())
    except LLMError:
        return None


def narrate(
    message: str,
    draft: str,
    build_client: Callable[[], MercuryClient | None] | None = None,
) -> str:
    """Rephrase `draft` via the model; the draft itself on any failure."""
    factory = build_client or _build_client
    try:
        client = factory()
    except LLMError:
        return draft
    if client is None:
        return draft
    try:
        return client.complete(
            SYSTEM, f"Operator asked: {message}\n\nDRAFT:\n{draft}", timeout_s=TIMEOUT_S
        )
    except LLMError:
        return draft
    finally:
        client.close()
