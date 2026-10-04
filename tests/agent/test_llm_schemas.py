"""LLM proposal schemas: valid proposals parse, anything else fails (Phase 12).

The contract compiler (Phase 13) may only consume validated proposals;
these tests pin the shapes it can rely on.
"""

import pytest
from pydantic import ValidationError

from agent.llm import schemas
from agent.llm.client import _strict_schema


def test_interpretation_round_trip():
    """A well-formed reading validates unchanged."""
    proposal = schemas.Interpretation.model_validate(
        {
            "summary": "Replace the damaged laptop",
            "goal": "customer has a working laptop",
            "requested_effects": ["replacement.create"],
            "mentioned_codes": ["ORD-1942", "TCK-101"],
            "ambiguities": [],
            "unsupported": False,
        }
    )
    assert proposal.requested_effects == ["replacement.create"]
    assert proposal.unsupported is False


def test_plan_proposal_requires_steps():
    """Empty plans are unrepresentable (the graph always has work)."""
    with pytest.raises(ValidationError):
        schemas.PlanProposal.model_validate({"steps": [], "notes": "none"})
    proposal = schemas.PlanProposal.model_validate(
        {
            "steps": [{"step": "find order", "tool": "search_order", "purpose": "bind IDs"}],
            "notes": "reads first",
        }
    )
    assert proposal.steps[0].tool == "search_order"


def test_next_action_rejects_unknown_shape():
    """Missing tool or rationale fails; extra params are data, not schema."""
    with pytest.raises(ValidationError):
        schemas.NextAction.model_validate({"tool": "get_order"})
    action = schemas.NextAction.model_validate(
        {
            "tool": "get_order",
            "params": {"order_id": "some-uuid", "amount_paise": 250000},
            "rationale": "bind the order",
        }
    )
    assert action.params["amount_paise"] == 250000


def test_summary_draft_is_lines_only():
    """Narrative carries no verdicts or values (packet ignores it anyway)."""
    draft = schemas.SummaryDraft.model_validate({"lines": ["Did the thing."]})
    assert draft.lines == ["Did the thing."]


@pytest.mark.parametrize(
    "model_cls",
    [
        schemas.Interpretation,
        schemas.PlanProposal,
        schemas.NextAction,
        schemas.SummaryDraft,
    ],
)
def test_strict_wire_schemas(model_cls):
    """Every proposal has a strict-mode schema: all fields required."""
    wire = _strict_schema(model_cls)
    assert "$defs" not in wire
    assert wire["type"] == "object"
    assert wire["additionalProperties"] is False
    assert sorted(wire["required"]) == sorted(wire["properties"])
