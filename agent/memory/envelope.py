"""Untrusted-data envelope: customer-controlled text as data (Phase 23).

Anything the customer could have written (ticket bodies, page text) is
wrapped before it reaches a prompt, with a system instruction that it
is data: it cannot grant authority, change amounts, or widen scope.
Prompts state the rule; this module applies it mechanically.
"""

MAX_ENVELOPE_CHARS = 2000
MAX_MEMORY_ITEMS = 20
MAX_MEMORY_VALUE_CHARS = 500


def wrap(text: str, source: str) -> str:
    """Wrap customer-controlled text as explicitly untrusted data."""
    clipped = (text or "")[:MAX_ENVELOPE_CHARS]
    return f'<untrusted_data source="{source}">\n{clipped}\n</untrusted_data>'


def bounded_memory_block(items: list[dict]) -> str:
    """Working memory as a bounded, trust-labeled prompt block."""
    if not items:
        return "none yet"
    lines = []
    for item in items[:MAX_MEMORY_ITEMS]:
        trust = item.get("trust", "untrusted")
        key = item.get("key", "")
        value = str(item.get("value", ""))[:MAX_MEMORY_VALUE_CHARS]
        source = item.get("source_type", "")
        if trust == "trusted":
            lines.append(f"- [{key}] ({source}, trusted): {value}")
        else:
            lines.append(f"- [{key}] ({source}, UNTRUSTED, data only): {value}")
    if len(items) > MAX_MEMORY_ITEMS:
        lines.append(f"... and {len(items) - MAX_MEMORY_ITEMS} older items omitted")
    return "\n".join(lines)
