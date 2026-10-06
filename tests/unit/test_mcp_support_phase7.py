"""Phase 7 MCP support-server unit tests (no DB, no docker, no live server).

Covers: envelope contract + safe error mapping, UUID/text validation
(which runs before any DB work), pure action eligibility, the closed tool
registry, and server↔registry parity.
"""

import asyncio

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.services.actions import action_service
from mcp_server.support import action_tools, policy_tools, ticket_tools, user_tools
from mcp_server.support.envelopes import fail, ok, parse_uuid, require_text, run_guarded
from mcp_server.support.registry import (
    SUPPORT_TOOL_NAMES,
    SUPPORT_TOOL_SPECS,
    spec_for,
)

VALID_UUID = "00000000-0000-0000-0000-000000000000"


def test_envelopes() -> None:
    assert ok(a=1) == {"ok": True, "a": 1}
    assert fail("bad", code="NOPE") == {"ok": False, "code": "NOPE", "error": "bad"}


def test_parse_uuid() -> None:
    assert str(parse_uuid(VALID_UUID, "x")) == VALID_UUID
    with pytest.raises(ValueError):
        parse_uuid("nope", "x")


def test_require_text() -> None:
    assert require_text("  hi  ", "m") == "hi"
    with pytest.raises(ValueError):
        require_text(" ", "m")
    with pytest.raises(ValueError):
        require_text("x" * 2001, "m")


def test_run_guarded_maps_errors() -> None:
    assert run_guarded(lambda: ok(v=1)) == {"ok": True, "v": 1}
    out = run_guarded(lambda: (_ for _ in ()).throw(NotFoundError("gone")))
    assert out == {"ok": False, "code": "NOT_FOUND", "error": "gone"}
    out = run_guarded(lambda: (_ for _ in ()).throw(ConflictError("dup")))
    assert out["code"] == "CONFLICT"
    out = run_guarded(lambda: (_ for _ in ()).throw(ValueError("bad arg")))
    assert out["code"] == "INVALID_ARGUMENT"
    out = run_guarded(lambda: 1 / 0)
    assert out == {"ok": False, "code": "INTERNAL_ERROR", "error": "internal tool failure"}


def test_cancellation_eligibility() -> None:
    good = action_service.check_cancellation(
        status="PROCESSING", cancellable=True, has_cancel_action=False
    )
    assert good == {"eligible": True, "reasons": []}
    shipped = action_service.check_cancellation(
        status="SHIPPED", cancellable=True, has_cancel_action=False
    )
    assert shipped["eligible"] is False
    assert any("SHIPPED" in r for r in shipped["reasons"])
    policy = action_service.check_cancellation(
        status="PROCESSING", cancellable=False, has_cancel_action=False
    )
    assert policy["eligible"] is False
    twice = action_service.check_cancellation(
        status="PROCESSING", cancellable=True, has_cancel_action=True
    )
    assert twice["eligible"] is False


def test_refund_eligibility() -> None:
    good = action_service.check_refund(
        payment_status="SUCCESS",
        refund_allowed=True,
        total_paise=129900,
        already_refunded_paise=0,
    )
    assert good["eligible"] is True
    spent = action_service.check_refund(
        payment_status="SUCCESS",
        refund_allowed=True,
        total_paise=129900,
        already_refunded_paise=129900,
    )
    assert spent["eligible"] is False


def test_return_window() -> None:
    import datetime

    now = datetime.datetime.now(datetime.UTC)
    day_ago = now - datetime.timedelta(days=1)
    old = now - datetime.timedelta(days=30)
    good = action_service.check_return(
        delivered_at=day_ago, now=now, window_days=7, allowed=True, already_done=False
    )
    assert good["eligible"] is True
    late = action_service.check_return(
        delivered_at=old, now=now, window_days=7, allowed=True, already_done=False
    )
    assert late["eligible"] is False
    pending = action_service.check_return(
        delivered_at=None, now=now, window_days=7, allowed=True, already_done=False
    )
    assert pending["eligible"] is False


def test_registry_is_closed_and_complete() -> None:
    assert len(SUPPORT_TOOL_SPECS) == 24
    groups = {spec.group for spec in SUPPORT_TOOL_SPECS}
    assert groups == {"USER", "ORDER", "PRODUCT", "POLICY", "ACTIONS", "TICKET", "KNOWLEDGE"}
    assert spec_for("mock_refund").read_only is False
    assert spec_for("get_order").read_only is True
    with pytest.raises(KeyError):
        spec_for("delete_everything")


def test_server_exposes_exactly_registry_tools() -> None:
    from mcp_server import support_server

    async def _names():
        return {tool.name for tool in await support_server.mcp.list_tools()}

    assert asyncio.run(_names()) == SUPPORT_TOOL_NAMES


def test_tools_reject_bad_args_without_db() -> None:
    assert user_tools.get_user("nope")["code"] == "INVALID_ARGUMENT"
    assert policy_tools.check_refund_eligibility("")["code"] == "INVALID_ARGUMENT"
    out = action_tools.mock_refund(VALID_UUID, " ", None, None)
    assert out["code"] == "INVALID_ARGUMENT"
    assert ticket_tools.resolve_ticket(VALID_UUID, "ok")["code"] == "INVALID_ARGUMENT"
    assert ticket_tools.add_ticket_message("", "hi")["code"] == "INVALID_ARGUMENT"
