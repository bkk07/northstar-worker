"""Task contract models: validated, capability-scoped work orders.

The contract is the deterministic bridge between an LLM interpretation
and everything downstream: policy scope, MCP capabilities, and (Phase 21)
verification. `status` drives the graph edge directly — `ok` plans,
`ambiguous` parks for clarification, `unsupported` ends inconclusive.
"""

from typing import Literal

from pydantic import BaseModel, Field

ContractStatus = Literal["ok", "ambiguous", "unsupported"]

BASE_CAPABILITIES = ("read", "read.fallback", "probe", "browser")


class ExpectedEffect(BaseModel):
    """One registry effect with fully bound, validated parameters."""

    effect: str = Field(min_length=1, description="Registry effect name")
    params: dict = Field(description="Bound IDs/values, schema-validated")
    capability: str = Field(min_length=1, description="MCP submit capability")


class EntityResolution(BaseModel):
    """Deterministic DB bindings for codes/names in the task text."""

    customer: dict | None = Field(default=None, description="Bound customer {id, code, name}")
    order: dict | None = Field(
        default=None, description="Bound order {id, code, customer_id, items}"
    )
    ticket: dict | None = Field(
        default=None, description="Bound ticket {id, code, customer_id, order_id}"
    )
    ambiguities: list[str] = Field(default_factory=list)
    unmatched_codes: list[str] = Field(default_factory=list)


class Contract(BaseModel):
    """Validated work order: what to do, to what, and with what scope."""

    task_id: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    customer_id: str | None = None
    order_id: str | None = None
    ticket_id: str | None = None
    effects: list[ExpectedEffect] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    ambiguity: list[str] = Field(default_factory=list)
    status: ContractStatus = "ok"
    snapshot_scope: dict = Field(
        default_factory=dict,
        description="Verifier scope: customer/order/ticket ID lists",
    )
    policy_scope: dict = Field(
        default_factory=dict,
        description="Policy scope: the bindings P-CAP/P-OWN enforce",
    )
