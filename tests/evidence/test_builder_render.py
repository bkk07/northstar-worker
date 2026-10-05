"""Packet assembly and rendering from facts only (Phase 24, no DB)."""

from agent.evidence.builder import build_packet, reconstruct_chain
from agent.evidence.render import render_markdown


def _packet(**overrides):
    base = {
        "task_id": "t",
        "run_id": "r",
        "task_text": "replace the damaged laptop",
        "status": "succeeded",
        "goal": "replace the damaged laptop",
        "effects": [
            {
                "effect": "replacement.create",
                "params": {"amount_paise": 0},
                "mutation_key": "k1",
            }
        ],
        "policy": {"outcome": "allow", "rule_id": "P-REP-001", "reason": "covered"},
        "policy_history": [{"outcome": "allow", "rule_id": "P-REP-001"}],
        "verification": {"verdict": "verified", "invariants": {"replacement_row": "pass"}},
        "journal": {"committed": ["browser_submit:k1"]},
        "memory": {"item_count": 3, "trusted": 2, "untrusted": 1, "injection_flags": []},
        "screenshots": [{"run_id": "r", "label": "after-submit", "path": "shots/after.png"}],
        "audit": {"events": 9, "first_seq": 41, "last_seq": 49},
    }
    base.update(overrides)
    return build_packet(**base)


def test_packet_has_every_section():
    """The packet cites proof, commits, policy, memory, shots, audit."""
    packet = _packet()
    assert packet["version"] == "evidence/v1"
    assert len(packet["summary"]) == 3
    assert packet["summary"][0].startswith("DONE")
    assert packet["effects"][0]["mutation_key"] == "k1"
    assert packet["policy"]["decision"]["rule_id"] == "P-REP-001"
    assert packet["verification"]["verdict"] == "verified"
    assert packet["journal"]["committed"] == ["browser_submit:k1"]
    assert packet["memory"]["trusted"] == 2
    assert packet["screenshots"][0]["path"] == "shots/after.png"
    assert packet["audit"] == {"events": 9, "first_seq": 41, "last_seq": 49}


def test_recovery_packet_tells_the_arc():
    """Recovery facts reach the summary and the journal section."""
    packet = _packet(
        journal={
            "committed": ["browser_submit:k2"],
            "recovered": True,
            "failure_type": "network_error",
            "strategies": ["retry_same"],
        }
    )
    assert packet["summary"][0].startswith("RECOVERY")
    assert packet["journal"]["strategies"] == ["retry_same"]


def test_empty_sections_render_placeholders():
    """Sections never vanish, even with nothing in them."""
    packet = _packet(effects=[], screenshots=[], journal={}, memory={})
    text = render_markdown(packet)
    assert "_No effects committed._" in text
    assert "_No screenshots captured._" in text
    assert "- committed effects: `none`" in text


def test_render_quotes_the_deciding_facts():
    """The manual read shows headline, rule, verdict, shots, audit pointer."""
    text = render_markdown(_packet())
    assert "DONE: replace the damaged laptop" in text
    assert "P-REP-001" in text
    assert "verdict: `verified`" in text
    assert "replacement_row: `pass`" in text
    assert "shots/after.png" in text
    assert "seq 41 → 49" in text
    assert "## Summary" in text and "## Audit" in text


def test_reconstruct_chain_replays_node_order():
    """Audit rows alone replay the run (first visits, seq order)."""
    events = [
        {"seq": 3, "kind": "node.transition", "node": "contract", "id": "c"},
        {"seq": 1, "kind": "run.start", "node": None, "id": "a"},
        {"seq": 2, "kind": "node.transition", "node": "understand", "id": "b"},
        {"seq": 4, "kind": "policy.decision", "node": "policy_check", "id": "d"},
        {"seq": 5, "kind": "node.transition", "node": "policy_check", "id": "e"},
    ]
    assert reconstruct_chain(events) == ["understand", "contract", "policy_check"]
