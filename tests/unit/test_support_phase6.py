"""Phase 6 support-console unit tests (no DB, no docker).

Covers: dashboard stat cards, manual-action guards, and support DTO
validation.
"""

import pytest
from pydantic import ValidationError

from app.core.exceptions import UnprocessableError
from app.schemas.support import EscalateCreate, ReplyCreate, ResolveCreate
from app.services.support import support_service


def test_summarize_stats_cards() -> None:
    stats = support_service.summarize_stats({"OPEN": 3, "ESCALATED": 1, "RESOLVED": 5})
    assert stats["summary"] == {"open": 3, "in_progress": 1, "waiting": 0, "resolved": 5}
    assert stats["by_status"]["OPEN"] == 3
    assert stats["by_status"]["AI_PROCESSING"] == 0
    assert stats["by_status"]["WAITING_FOR_HUMAN"] == 0


def test_summarize_stats_empty_and_closed() -> None:
    stats = support_service.summarize_stats({})
    assert stats["summary"] == {"open": 0, "in_progress": 0, "waiting": 0, "resolved": 0}
    stats = support_service.summarize_stats({"CLOSED": 2})
    assert stats["summary"]["resolved"] == 2


def test_action_allowed_on_actionable() -> None:
    support_service.ensure_action_allowed("OPEN", "reply")
    support_service.ensure_action_allowed("ESCALATED", "resolve")


def test_action_rejected_on_terminal() -> None:
    with pytest.raises(UnprocessableError):
        support_service.ensure_action_allowed("RESOLVED", "reply")
    with pytest.raises(UnprocessableError):
        support_service.ensure_action_allowed("CLOSED", "escalate")


def test_reply_dto_validation() -> None:
    with pytest.raises(ValidationError):
        ReplyCreate(message="")
    assert ReplyCreate(message="Looking into this.").message.startswith("Looking")


def test_resolve_dto_validation() -> None:
    with pytest.raises(ValidationError):
        ResolveCreate(resolution="ok")
    ok = ResolveCreate(resolution="Refund issued for the damaged item.")
    assert ok.resolution.startswith("Refund")


def test_escalate_reason_optional() -> None:
    assert EscalateCreate().reason is None
    assert EscalateCreate(reason="Needs a supervisor.").reason is not None
