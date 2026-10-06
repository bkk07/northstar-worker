"""AI agent controller (Phase 9, `SUPPORT_AGENT` only).

Solve a ticket with the AI, watch the live activity stream, decide HITL
approvals, and take tickets back. The LLM client is Groq when configured,
otherwise the deterministic mock path runs (never a surprise model call).
"""

import asyncio
import json

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from agent.llm.client import LLMError, MercuryClient, config_from_env
from app.core.auth import decode_access_token, require_roles
from app.core.deps import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.schemas.support import (
    ApprovalDecision,
    ApprovalRead,
    ApprovalResult,
    SolveResponse,
    TakeoverResult,
    TraceResponse,
)
from app.services.agent_run import agent_run_service, bus

router = APIRouter(tags=["agent"])
_staff = require_roles("SUPPORT_AGENT")

TERMINAL_EVENTS = {"ticket_resolved", "run_completed", "approval_rejected", "taken_over"}


def _llm_client():
    """Groq client when configured, else the mock path (`None`)."""
    try:
        return MercuryClient(config_from_env())
    except LLMError:
        return None


@router.post("/support/tickets/{ticket_id}/solve", response_model=SolveResponse)
def solve_ticket(
    ticket_id: str,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> dict:
    """Run the AI support agent on a ticket (classify → act → pause/resolve)."""
    client = _llm_client()
    try:
        return agent_run_service.solve(session, ticket_id=ticket_id, llm=client)
    finally:
        if client is not None:
            client.close()


@router.get("/support/tickets/{ticket_id}/trace", response_model=TraceResponse)
def get_trace(
    ticket_id: str,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> dict:
    """Persisted AI timeline + approvals for one ticket."""
    return agent_run_service.get_trace(session, ticket_id=ticket_id)


@router.get("/support/approvals", response_model=list[ApprovalRead])
def list_approvals(
    status: str | None = None,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> list[dict]:
    """Approval queue (default PENDING) with ticket context."""
    return agent_run_service.list_approvals(session, status=status)


@router.post("/support/approvals/{approval_id}/decision", response_model=ApprovalResult)
def decide_approval(
    approval_id: str,
    payload: ApprovalDecision,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> dict:
    """Approve (execute → verify → resolve) or reject a pending approval."""
    return agent_run_service.decide_approval(
        session,
        approval_id=approval_id,
        staff_id=str(claims["sub"]),
        approved=payload.approved,
        note=payload.note,
    )


@router.post("/support/tickets/{ticket_id}/takeover", response_model=TakeoverResult)
def take_over(
    ticket_id: str,
    claims: dict = Depends(_staff),
    session: Session = Depends(get_db),
) -> dict:
    """Staff takes a ticket back from the AI (cancels the active run)."""
    return agent_run_service.take_over(
        session, ticket_id=ticket_id, staff_id=str(claims["sub"])
    )


@router.get("/support/tickets/{ticket_id}/activity")
async def activity_stream(
    ticket_id: str,
    token: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
) -> EventSourceResponse:
    """Live AI activity events (SSE; history comes from `/trace`).

    EventSource cannot send headers, so the staff token may arrive as
    `?token=` for this stream only (prototype scope).
    """
    raw = token
    if not raw and authorization:
        raw = authorization[7:] if authorization.startswith("Bearer ") else authorization
    if not raw:
        raise UnauthorizedError("bearer token required")
    claims = decode_access_token(raw)
    if claims.get("role") != "SUPPORT_AGENT":
        raise ForbiddenError("insufficient role")
    queue = bus.subscribe(ticket_id)

    async def _events():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                except TimeoutError:
                    yield {"event": "heartbeat", "data": "{}"}
                    continue
                yield {"event": event["type"], "data": json.dumps(event["data"])}
                if event["type"] in TERMINAL_EVENTS:
                    break
        finally:
            bus.unsubscribe(ticket_id, queue)

    return EventSourceResponse(_events())
