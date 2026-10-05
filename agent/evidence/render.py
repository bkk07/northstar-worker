"""Evidence packet rendering: operator-readable markdown.

Renders the packet the builder assembles — the manual end-to-end read
(`docs/demo.md` holds generated samples). Untrusted page text never
enters the packet, so rendering quotes no customer-controlled strings
beyond the operator's own task text.
"""

from collections.abc import Mapping, Sequence


def render_markdown(packet: Mapping) -> str:
    """One markdown document for a terminal run."""
    lines = [
        f"# Evidence: {packet.get('task_text', '')}",
        "",
        f"Status: `{packet.get('status', '')}` · "
        f"task `{packet.get('task_id', '')}` · run `{packet.get('run_id', '')}`",
        "",
        "## Summary",
        "",
        *[f"- {line}" for line in packet.get("summary", [])],
        "",
        "## Effects",
        "",
        *_section_lines(packet.get("effects", []), _effect_line, "_No effects committed._"),
        "",
        "## Policy",
        "",
        *_policy_lines(packet.get("policy", {})),
        "",
        "## Verification",
        "",
        *_verification_lines(packet.get("verification", {})),
        "",
        "## Recovery",
        "",
        *_journal_lines(packet.get("journal", {})),
        "",
        "## Memory",
        "",
        *_memory_lines(packet.get("memory", {})),
        "",
        "## Screenshots",
        "",
        *_section_lines(
            packet.get("screenshots", []),
            lambda shot: f"- `{shot.get('label', '')}`: `{shot.get('path', '')}`",
            "_No screenshots captured._",
        ),
        "",
        "## Audit",
        "",
        _audit_line(packet.get("audit", {})),
        "",
    ]
    return "\n".join(lines)


def _section_lines(items: Sequence[Mapping], render, empty: str) -> list[str]:
    """Rendered items, or the empty placeholder (sections never vanish)."""
    if not items:
        return [empty]
    return [render(item) for item in items]


def _effect_line(effect: Mapping) -> str:
    """One committed effect with its journal key."""
    params = effect.get("params", {})
    amount = params.get("amount_paise")
    extra = f" Rs.{amount / 100:,.2f}" if isinstance(amount, (int, float)) else ""
    return f"- `{effect.get('effect', '')}`{extra} (key `{effect.get('mutation_key', '')}`)"


def _policy_lines(policy: Mapping) -> list[str]:
    """The deciding rule plus its history."""
    decision = policy.get("decision", {})
    lines = [
        f"- outcome: `{decision.get('outcome', '')}` "
        f"rule `{decision.get('rule_id', '')}` — {decision.get('reason', '')}".rstrip()
    ]
    for entry in policy.get("history", []):
        lines.append(f"- {entry.get('outcome', '')} `{entry.get('rule_id', '')}`")
    return lines


def _verification_lines(verification: Mapping) -> list[str]:
    """Verdict plus the invariant outcomes that prove it."""
    lines = [f"- verdict: `{verification.get('verdict', '')}`"]
    invariants = verification.get("invariants", {})
    if isinstance(invariants, dict):
        for name, outcome in invariants.items():
            lines.append(f"- {name}: `{outcome}`")
    return lines


def _journal_lines(journal: Mapping) -> list[str]:
    """Commits, recovery arc, and strategies (journal facts only)."""
    committed = journal.get("committed", [])
    lines = (
        [f"- committed effects: `{', '.join(str(c) for c in committed)}`"]
        if committed
        else ["- committed effects: `none`"]
    )
    if journal.get("recovered"):
        arc = f"- recovered from `{journal.get('failure_type', '')}`"
        if journal.get("strategies"):
            arc += f" via {', '.join(str(s) for s in journal['strategies'])}"
        lines.append(arc)
    return lines


def _memory_lines(memory: Mapping) -> list[str]:
    """Provenance counts and injection flags (no raw page text)."""
    lines = [
        f"- items: {memory.get('item_count', 0)} "
        f"({memory.get('trusted', 0)} trusted / {memory.get('untrusted', 0)} untrusted)"
    ]
    for flag in memory.get("injection_flags", []):
        lines.append(f"- injection flag: `{flag}`")
    return lines


def _audit_line(audit: Mapping) -> str:
    """The chain pointer: replay from first to last sequence number."""
    return (
        f"- {audit.get('events', 0)} events, "
        f"seq {audit.get('first_seq')} → {audit.get('last_seq')} "
        f"(replay `GET /api/tasks/{{id}}/events/history`)"
    )
