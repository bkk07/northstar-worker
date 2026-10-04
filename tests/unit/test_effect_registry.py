"""Phase 3: effect registry is closed, typed, and schema-validated."""

import pytest
from pydantic import ValidationError

from agent.contract.effect_registry import (
    EFFECT_REGISTRY,
    RefundCreateParams,
    TicketNoteParams,
    UnknownEffectError,
    get_effect,
)
from northstar_common.enums import EffectType


def test_registry_covers_every_effect_type():
    assert set(EFFECT_REGISTRY) == set(EffectType)


def test_lookup_by_enum_and_dotted_name():
    by_enum = get_effect(EffectType.REFUND_CREATE)
    by_name = get_effect("refund.create")
    assert by_enum is by_name
    assert by_enum.capability == "refund.create"
    assert by_enum.ops_route.startswith("/ops/")


def test_out_of_registry_effects_rejected():
    with pytest.raises(UnknownEffectError):
        get_effect("coupon.apply")
    with pytest.raises(UnknownEffectError):
        get_effect(EffectType("ticket.note").value + ".extra")


def test_refund_schema_validation():
    valid = RefundCreateParams(order_id="o1", ticket_id="t1", amount_paise=250000)
    assert valid.amount_paise == 250000
    with pytest.raises(ValidationError):
        RefundCreateParams(order_id="o1", ticket_id="t1", amount_paise=0)
    with pytest.raises(ValidationError):
        RefundCreateParams(order_id="o1", ticket_id="t1", amount_paise=-5)


def test_note_kind_restricted():
    TicketNoteParams(ticket_id="t1", kind="internal", body="hello")
    with pytest.raises(ValidationError):
        TicketNoteParams(ticket_id="t1", kind="sms", body="hello")
