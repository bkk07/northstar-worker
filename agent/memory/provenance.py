"""Memory provenance: every item carries its source and trust (Phase 23).

Trust is a property of the source, assigned deterministically here —
never by the LLM. Facts from untrusted sources (ticket bodies, page
text, browser output) stay untrusted until a deterministic cross-check
against a database fact promotes them into a separate trusted item.
"""

TRUSTED = "trusted"
UNTRUSTED = "untrusted"

# Source types the memory store accepts (plan §22). Operator and machine
# sources are trusted; customer-controlled and page sources are not.
SOURCE_TRUST = {
    "user": TRUSTED,
    "operator": TRUSTED,
    "database": TRUSTED,
    "api": TRUSTED,
    "policy": TRUSTED,
    "ticket": UNTRUSTED,
    "page": UNTRUSTED,
    "browser": UNTRUSTED,
}


def classify(source_type: str) -> str:
    """Trust for a source type (unknown sources fail closed to untrusted)."""
    return SOURCE_TRUST.get(source_type, UNTRUSTED)


def is_trusted(source_type: str) -> bool:
    """True only for the explicitly trusted sources."""
    return classify(source_type) == TRUSTED
