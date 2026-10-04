"""Structured LLM proposals: the shapes Mercury 2.5 must return.

The LLM proposes; deterministic code disposes. Every field is required
so the wire schema is strict-mode compatible, and every proposal is
validated here before any node trusts it. Amounts and entity IDs enter
the contract only from operator/DB facts (Phase 13), never from these
models directly — they are proposals, not authority.
"""

from typing import Any

from pydantic import BaseModel, Field


class Interpretation(BaseModel):
    """`understand`: what the operator asked, as typed data."""

    summary: str = Field(min_length=1, description="One-line reading of the task")
    goal: str = Field(min_length=1, description="Desired end state in own words")
    requested_effects: list[str] = Field(description="Effect-type guesses from the closed registry")
    mentioned_codes: list[str] = Field(
        description="Human codes quoted in the text (C102, ORD-1942, TCK-101)"
    )
    mentioned_names: list[str] = Field(
        description="Person names quoted in the text (customer identity candidates)"
    )
    ambiguities: list[str] = Field(description="Questions only the operator can settle")
    unsupported: bool = Field(description="True when no registry effect fits")


class PlanStep(BaseModel):
    """One ordered step over a registered tool."""

    step: str = Field(min_length=1, description="What this step achieves")
    tool: str = Field(min_length=1, description="Registered tool name")
    purpose: str = Field(min_length=1, description="Why this step is needed")


class PlanProposal(BaseModel):
    """`plan`: ordered steps from facts to verification."""

    steps: list[PlanStep] = Field(min_length=1)
    notes: str = Field(description="Assumptions the operator should see")


class NextAction(BaseModel):
    """`decide`: the single next typed action."""

    tool: str = Field(min_length=1, description="Registered tool name")
    params: dict[str, Any] = Field(description="Tool arguments (validated in Phase 14)")
    rationale: str = Field(min_length=1, description="Why this action now")


class SummaryDraft(BaseModel):
    """`finalize`: optional narrative lines (never packet values)."""

    lines: list[str] = Field(
        description="Operator-facing narrative; the evidence packet ignores it"
    )
