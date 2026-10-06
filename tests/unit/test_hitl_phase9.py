"""Phase 9 HITL/run-service unit tests (no DB, no model calls, no docker).

Covers: the pure activity-timeline builder, the in-process event bus, and
JSON-safe coercion. DB-backed solve/approve paths are exercised by hand
against a live backend (prototype demo), not here.
"""

import asyncio

from app.services.agent_run import bus
from app.services.agent_run.agent_run_service import _jsonable, build_trace


def _run(**overrides):
    base = {
        "id": "r1",
        "status": "COMPLETED",
        "intent": "REFUND",
        "decision": "resolved_ready",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def test_trace_idle_without_run() -> None:
    steps = build_trace(None, [], [], "OPEN")
    assert len(steps) == 1 and steps[0]["state"] == "todo"


def test_trace_full_success() -> None:
    tools = [
        {"id": "c1", "tool_name": "get_order", "status": "DONE"},
        {"id": "c2", "tool_name": "check_refund_eligibility", "status": "DONE"},
        {"id": "c3", "tool_name": "mock_refund", "status": "DONE"},
    ]
    approvals = [
        {
            "id": "a1",
            "action_type": "REFUND",
            "status": "APPROVED",
            "requested_at": "t",
            "resolved_at": "t2",
        }
    ]
    steps = build_trace(_run(), tools, approvals, "RESOLVED")
    labels = [s["label"] for s in steps]
    assert "AI started" in labels
    assert "Ticket classified as REFUND" in labels
    assert "Order found" in labels
    assert "Refund eligibility checked" in labels
    assert "Mock refund created" in labels
    assert "Action verified" in labels
    assert "Ticket resolved" in labels
    assert all(s["state"] == "done" for s in steps)


def test_trace_pending_approval_active() -> None:
    approvals = [
        {
            "id": "a1",
            "action_type": "REFUND",
            "status": "PENDING",
            "requested_at": "t",
            "resolved_at": None,
        }
    ]
    steps = build_trace(_run(decision="awaiting_approval"), [], approvals, "WAITING_FOR_HUMAN")
    waiting = next(s for s in steps if s["key"] == "waiting")
    assert waiting["state"] == "active"
    assert "Ticket resolved" not in [s["label"] for s in steps]


def test_jsonable_coercion() -> None:
    assert _jsonable({"a": ("x", 1, None)}) == {"a": ["x", 1, None]}
    assert _jsonable(object()) .startswith("<")


def test_bus_emit_and_subscribe() -> None:
    async def _run_bus():
        queue = bus.subscribe("t1")
        try:
            bus.emit("t1", "ai_started", {"run_id": "r1"})
            event = await asyncio.wait_for(queue.get(), timeout=2.0)
            assert event["type"] == "ai_started"
            assert event["data"] == {"run_id": "r1"}
        finally:
            bus.unsubscribe("t1", queue)

    asyncio.run(_run_bus())
