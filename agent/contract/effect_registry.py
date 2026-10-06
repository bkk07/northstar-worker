"""Effect registry: the closed set of workflows the agent may perform.

New workflows are added here (effect type + form-flow hints + expected-state
schema + policy rules + verification invariant) with no new graph nodes,
tool code, or task-name branches (plan §28). The contract compiler
(Phase 13) binds proposals to these entries; anything outside the
registry ends INCONCLUSIVE, never improvised.
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, PositiveInt

from northstar_common.enums import EffectType, PolicyRuleId
from northstar_common.errors import NorthstarError


class UnknownEffectError(NorthstarError):
    """Requested effect is outside the registry."""

    code = "UNKNOWN_EFFECT"


class ReplacementCreateParams(BaseModel):
    """Expected state for `replacement.create`."""

    order_id: str = Field(min_length=1)
    order_item_id: str = Field(min_length=1)
    ticket_id: str = Field(min_length=1)
    reason: str | None = None


class RefundCreateParams(BaseModel):
    """Expected state for `refund.create` (amount always in paise)."""

    order_id: str = Field(min_length=1)
    ticket_id: str = Field(min_length=1)
    amount_paise: PositiveInt


class TicketNoteParams(BaseModel):
    """Expected state for `ticket.note`."""

    ticket_id: str = Field(min_length=1)
    kind: Literal["internal", "customer_reply"]
    body: str = Field(min_length=1)


class TicketStatusParams(BaseModel):
    """Expected state for `ticket.status`."""

    ticket_id: str = Field(min_length=1)
    to_status: Literal["open", "in_progress", "waiting_on_customer", "resolved", "closed"]


class TicketReplyParams(BaseModel):
    """Expected state for `ticket.reply` (customer-visible)."""

    ticket_id: str = Field(min_length=1)
    body: str = Field(min_length=1)


@dataclass(frozen=True)
class EffectDefinition:
    """One registry entry: what the effect is, where it happens in `/ops`,
    what valid parameters look like, which policy rules govern it, and
    which verifier invariant proves it."""

    effect: EffectType
    capability: str
    description: str
    ops_route: str
    form_fields: tuple[str, ...]
    expected_schema: type[BaseModel]
    policy_rules: tuple[PolicyRuleId, ...]
    invariant: str


EFFECT_REGISTRY: dict[EffectType, EffectDefinition] = {
    EffectType.REPLACEMENT_CREATE: EffectDefinition(
        effect=EffectType.REPLACEMENT_CREATE,
        capability="replacement.create",
        description="Ship a replacement for a damaged/eligible order item.",
        ops_route="/ops/tickets/:code",
        form_fields=("order_id", "order_item_id", "ticket_id", "reason"),
        expected_schema=ReplacementCreateParams,
        policy_rules=(
            PolicyRuleId.E_REPL_001,
            PolicyRuleId.P_CAP_001,
            PolicyRuleId.P_OWN_001,
            PolicyRuleId.P_REPL_001,
            PolicyRuleId.P_REPL_002,
            PolicyRuleId.P_DUP_001,
            PolicyRuleId.P_FAIL_CLOSED,
        ),
        invariant="replacement",
    ),
    EffectType.REFUND_CREATE: EffectDefinition(
        effect=EffectType.REFUND_CREATE,
        capability="refund.create",
        description="Refund an amount (paise) against a paid order.",
        ops_route="/ops/tickets/:code",
        form_fields=("order_id", "ticket_id", "amount_paise"),
        expected_schema=RefundCreateParams,
        policy_rules=(
            PolicyRuleId.E_REF_001,
            PolicyRuleId.E_REF_002,
            PolicyRuleId.P_CAP_001,
            PolicyRuleId.P_OWN_001,
            PolicyRuleId.P_REF_001,
            PolicyRuleId.P_REF_002,
            PolicyRuleId.P_REF_003,
            PolicyRuleId.P_REF_004,
            PolicyRuleId.P_DUP_001,
            PolicyRuleId.P_FAIL_CLOSED,
        ),
        invariant="refund",
    ),
    EffectType.TICKET_NOTE: EffectDefinition(
        effect=EffectType.TICKET_NOTE,
        capability="ticket.note",
        description="Attach an internal note to the contract's own ticket.",
        ops_route="/ops/tickets/:id/notes",
        form_fields=("ticket_id", "kind", "body"),
        expected_schema=TicketNoteParams,
        policy_rules=(PolicyRuleId.P_CAP_001, PolicyRuleId.P_NOTE_001, PolicyRuleId.P_FAIL_CLOSED),
        invariant="ticket",
    ),
    EffectType.TICKET_STATUS: EffectDefinition(
        effect=EffectType.TICKET_STATUS,
        capability="ticket.status",
        description="Move the contract's own ticket to a new status.",
        ops_route="/ops/tickets/:id/status",
        form_fields=("ticket_id", "to_status"),
        expected_schema=TicketStatusParams,
        policy_rules=(PolicyRuleId.P_CAP_001, PolicyRuleId.P_NOTE_001, PolicyRuleId.P_FAIL_CLOSED),
        invariant="ticket",
    ),
    EffectType.TICKET_REPLY: EffectDefinition(
        effect=EffectType.TICKET_REPLY,
        capability="ticket.reply",
        description="Send a customer-visible reply on the contract's ticket.",
        ops_route="/ops/tickets/:id/reply",
        form_fields=("ticket_id", "body"),
        expected_schema=TicketReplyParams,
        policy_rules=(PolicyRuleId.P_CAP_001, PolicyRuleId.P_NOTE_001, PolicyRuleId.P_FAIL_CLOSED),
        invariant="ticket",
    ),
}


def get_effect(effect: EffectType | str) -> EffectDefinition:
    """Resolve a registry entry by enum or dotted name.

    Raises UnknownEffectError for anything outside the registry, so new
    workflows must be registered deliberately (plan Test J).
    """
    key: EffectType
    try:
        key = effect if isinstance(effect, EffectType) else EffectType(effect)
    except ValueError:
        raise UnknownEffectError(f"effect outside registry: {effect!r}") from None
    try:
        return EFFECT_REGISTRY[key]
    except KeyError:
        raise UnknownEffectError(f"effect outside registry: {effect!r}") from None
