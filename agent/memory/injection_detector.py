"""Injection detector: deterministic flags for prompt-injection text.

The LLM never judges injections; these regexes run over every
customer-controlled string before it reaches memory or a prompt. A flag
does not block by itself (policy decides from trusted facts) — it marks
the item untrusted and auditable, and the S5 arc proves injected
payouts still BLOCK with no mutation.
"""

import base64
import re

ROLE_PLAY = re.compile(
    r"\b(you are (now )?|pretend (to be|you are)|act as|roleplay as|"
    r"you('re| are) (an? )?(admin|manager|owner|support agent|system))\b",
    re.IGNORECASE,
)
SYSTEM_OVERRIDE = re.compile(
    r"\b(ignore|disregard|override|forget|bypass)\b[^.\n]{0,40}?\binstructions\b",
    re.IGNORECASE,
)
AUTHORITY_CLAIM = re.compile(
    r"\b(pre.?approved|pre.?authorized|manager approved|already approved|"
    r"authorized by|per policy exception|urgent override)\b",
    re.IGNORECASE,
)
AMOUNT_DIRECTIVE = re.compile(
    r"(?:\b(payout|pay out|transfer|send|release|disburse)\b[^.\n]{0,80}?"
    r"(?:Rs\.?|₹|INR)\s*[\d,]+"
    r"|(?:Rs\.?|₹|INR)\s*[\d,]+[^.\n]{0,80}?\bpayout\b)",
    re.IGNORECASE,
)
SCOPE_WIDEN = re.compile(
    r"\b(all customers|every order|all orders|any ticket|other customers'? orders?)\b",
    re.IGNORECASE,
)
ENCODABLE_RUN = re.compile(r"[A-Za-z0-9+/=]{60,}")

PATTERNS = (
    ("role_play", ROLE_PLAY),
    ("system_override", SYSTEM_OVERRIDE),
    ("authority_claim", AUTHORITY_CLAIM),
    ("amount_directive", AMOUNT_DIRECTIVE),
    ("scope_widening", SCOPE_WIDEN),
)


def detect(text: str) -> list[str]:
    """Flag codes for injection patterns in customer-controlled text."""
    found = []
    for code, pattern in PATTERNS:
        if pattern.search(text or ""):
            found.append(code)
    if _has_encoded_payload(text or ""):
        found.append("encoded_text")
    return found


def _has_encoded_payload(text: str) -> bool:
    """Long base64 runs that decode to text (smuggled instructions)."""
    for match in ENCODABLE_RUN.findall(text):
        try:
            decoded = base64.b64decode(match, validate=True).decode("utf-8", "ignore")
        except Exception:
            continue
        if len(decoded) >= 20 and re.search(r"[a-zA-Z]{3,}", decoded):
            return True
    return False
