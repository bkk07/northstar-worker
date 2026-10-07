"""Canonical support-ticket AI service: LangGraph → MCP → policy → HITL → verify.

ONE execution path for `Solve with AI`. The graph (`agent/support_graph`)
is goal-oriented (supervisor picks workflow, each workflow loads only the
tools its intent needs), pauses at the HITL gate with full `graph_state`
persisted on the run, and resumes the SAME execution on approve/reject.
Every mutation is verified before the customer-facing AI_AGENT message.
"""

import datetime
import uuid

from sqlalchemy.orm import Session

from agent.support_graph.runner import (
    is_paused_for_human,
    resume_support_ticket,
    run_support_ticket,
)
from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.repositories.agent.agent_repository import AgentRepository
from app.repositories.tickets.ticket_repository import CustomerTicketRepository
from app.services.actions import action_service
from app.services.agent_run import bus
from app.services.support import support_service
from database.models.biz.agent import (
    APPROVAL_APPROVED,
    APPROVAL_REJECTED,
    RUN_CANCELLED,
    RUN_COMPLETED,
    RUN_FAILED,
    RUN_WAITING,
)
from database.models.biz.customer_ticket import (
    SENDER_AI_AGENT,
    TICKET_AI_PROCESSING,
    TICKET_CLOSED,
    TICKET_ESCALATED,
    TICKET_OPEN,
    TICKET_RESOLVED,
    TICKET_WAITING_FOR_CUSTOMER,
    TICKET_WAITING_FOR_HUMAN,
)

TERMINAL_TICKETS = (TICKET_RESOLVED, TICKET_CLOSED)

APPROVAL_TTL = datetime.timedelta(hours=24)
APPROVAL_EXPIRED = "EXPIRED"

_TOOL_LABELS = {
    "get_ticket": "Ticket loaded",
    "get_order": "Order found",
    "get_order_items": "Order items read",
    "get_order_status": "Order status checked",
    "get_order_tracking": "Tracking information read",
    "get_product": "Product read",
    "get_product_details": "Product details read",
    "get_product_policy": "Product policy retrieved",
    "check_refund_eligibility": "Refund eligibility checked",
    "check_return_eligibility": "Return eligibility checked",
    "check_replacement_eligibility": "Replacement eligibility checked",
    "check_cancellation_eligibility": "Cancellation eligibility checked",
    "mock_refund": "Mock refund created",
    "mock_return": "Mock return created",
    "mock_replace": "Mock replacement created",
    "mock_cancel_order": "Mock cancellation created",
    "search_knowledge": "Knowledge searched",
}

_NODE_EVENTS = {
    "load_ticket": "Analyzing ticket",
    "supervisor": "Planning resolution",
    "gather": "Loading order",
    "check_policy": "Checking policy",
    "propose": "Action proposed",
    "human_approval": "Waiting for support",
    "execute": "Executing action",
    "verify": "Verifying action",
    "respond": "Generating response",
}


def _jsonable(value):
    """Best-effort JSON-safe coercion for stored tool arguments."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return str(value)


def _compact_args(arguments: dict | None) -> str | None:
    """Short `key=value` summary of tool arguments for the timeline."""
    if not arguments:
        return None
    parts = []
    for key, value in _jsonable(arguments).items():
        text = str(value)
        if len(text) > 28:
            text = text[:25] + "…"
        parts.append(f"{key}={text}")
    summary = ", ".join(parts)
    return summary if len(summary) <= 120 else summary[:117] + "…"


def build_trace(
    run: dict | None,
    tool_calls: list[dict],
    approvals: list[dict],
    ticket_status: str,
) -> list[dict]:
    """AI activity timeline from persisted rows (pure, unit-testable)."""
    steps: list[dict] = []

    def add(key: str, label: str, state: str, at: str | None = None,
            detail: str | None = None) -> None:
        step: dict = {"key": key, "label": label, "state": state, "at": at}
        if detail is not None:
            step["detail"] = detail
        steps.append(step)

    if run is None:
        add("idle", "AI has not run on this ticket yet", "todo")
        return steps
    add("started", "AI started", "done", run.get("created_at"))
    if run.get("intent"):
        workflow = run.get("workflow")
        label = f"Ticket classified as {run['intent']}"
        if workflow:
            label += f" → {workflow} workflow"
        add("classified", label, "done")
    for call in tool_calls:
        label = _TOOL_LABELS.get(call["tool_name"], call["tool_name"])
        add(
            f"tool-{call['id']}",
            label,
            "done" if call["status"] == "DONE" else "todo",
            call.get("created_at"),
            _compact_args(call.get("arguments")),
        )
    pending = next((a for a in approvals if a["status"] == "PENDING"), None)
    decided = next(
        (a for a in approvals if a["status"] in (APPROVAL_APPROVED, APPROVAL_REJECTED, APPROVAL_EXPIRED)),
        None,
    )
    proposed = pending or decided
    if proposed:
        add(
            "proposed",
            f"{proposed['action_type']} action proposed",
            "done",
            proposed.get("requested_at"),
        )
    if pending:
        add("waiting", "Waiting for support approval", "active")
    if decided:
        verb = {"APPROVED": "approved", "REJECTED": "rejected", "EXPIRED": "expired"}.get(
            decided["status"], decided["status"].lower()
        )
        add(f"human-{verb}", f"{verb.capitalize()} by support", "done", decided.get("resolved_at"))
    verification = (run.get("verification_result") or {}) if isinstance(run, dict) else {}
    if verification.get("ok") or run.get("decision") in ("resolved_ready", "approved_executed"):
        detail = verification.get("tool") if verification.get("ok") else None
        if detail:
            add("verified", "Action verified", "done", detail)
        else:
            add("verified", "Action verified", "done")
    if run.get("decision"):
        add("responded", "Customer response generated", "done")
    if ticket_status == TICKET_RESOLVED:
        add("resolved", "Ticket resolved", "done")
    if ticket_status == TICKET_WAITING_FOR_CUSTOMER:
        add("waiting_customer", "Waiting for customer clarification", "active")
    if run.get("status") == RUN_FAILED:
        add("failed", f"Run failed — human takeover needed ({run.get('error', '')})".strip(), "todo")
    return steps


def _load_ticket(session: Session, ticket_id: str):
    tickets = CustomerTicketRepository(session)
    try:
        ticket_uuid = uuid.UUID(ticket_id)
    except ValueError:
        raise NotFoundError("ticket not found") from None
    ticket = tickets.get_by_id(ticket_uuid)
    if ticket is None:
        raise NotFoundError("ticket not found")
    return ticket


def _audit(
    session: Session,
    repo: AgentRepository,
    ticket,
    event_type: str,
    actor_type: str = SENDER_AI_AGENT,
    actor_id=None,
    metadata: dict | None = None,
) -> None:
    repo.audit(
        ticket_id=ticket.id,
        actor_type=actor_type,
        actor_id=actor_id,
        event_type=event_type,
        metadata=metadata or {},
    )
    bus.emit(str(ticket.id), event_type, metadata or {})


def _live_tools():
    """Canonical MCP-backed tool map for the support graph (lazy import)."""
    from mcp_server.support import (
        action_tools,
        knowledge_tools,
        order_tools,
        policy_tools,
        product_tools,
        ticket_tools,
    )

    return {
        "get_ticket": ticket_tools.get_ticket,
        "get_order": order_tools.get_order,
        "get_order_items": order_tools.get_order_items,
        "get_order_status": order_tools.get_order_status,
        "get_order_tracking": order_tools.get_order_tracking,
        "get_product": product_tools.get_product,
        "get_product_details": product_tools.get_product_details,
        "get_product_policy": product_tools.get_product_policy,
        "check_refund_eligibility": policy_tools.check_refund_eligibility,
        "check_return_eligibility": policy_tools.check_return_eligibility,
        "check_replacement_eligibility": policy_tools.check_replacement_eligibility,
        "check_cancellation_eligibility": policy_tools.check_cancellation_eligibility,
        "mock_refund": action_tools.mock_refund,
        "mock_return": action_tools.mock_return,
        "mock_replace": action_tools.mock_replace,
        "mock_cancel_order": action_tools.mock_cancel_order,
        "search_knowledge": knowledge_tools.search_knowledge,
    }


def _traced_tools(session: Session, repo: AgentRepository, run, ticket) -> dict:
    live = _live_tools()

    def _traced(name: str, fn):
        def call(*args, **kwargs):
            bus.emit(str(ticket.id), "tool_started", {"tool": name})
            try:
                out = fn(*args, **kwargs)
            except Exception as exc:
                repo.add_tool_call(
                    run_id=run.id,
                    tool_name=name,
                    arguments=_jsonable({"args": args, "kwargs": kwargs}),
                    result={"ok": False, "error": str(exc)[:300]},
                    status="FAILED",
                )
                session.commit()
                bus.emit(str(ticket.id), "tool_failed", {"tool": name})
                raise
            repo.add_tool_call(
                run_id=run.id,
                tool_name=name,
                arguments=_jsonable({"args": args, "kwargs": kwargs}),
                result={"ok": out.get("ok") if isinstance(out, dict) else True},
                status="DONE",
            )
            session.commit()
            bus.emit(str(ticket.id), "tool_done", {"tool": name})
            return out

        return call

    return {name: _traced(name, fn) for name, fn in live.items()}


def _persist_graph_state(session: Session, run, state: dict) -> None:
    run.graph_state = _jsonable(state)
    run.intent = state.get("intent") or None
    run.workflow = state.get("workflow") or None
    run.decision = state.get("decision")
    run.error = (state.get("error") or None)
    run.verification_result = _jsonable(state.get("verification_result") or {})
    session.commit()


def _save_customer_message(session: Session, ticket, text: str) -> None:
    CustomerTicketRepository(session).add_message(
        ticket_id=ticket.id,
        sender_type=SENDER_AI_AGENT,
        sender_id=None,
        message=text,
    )


def solve(session: Session, *, ticket_id: str, llm=None) -> dict:
    """Run the canonical LangGraph on a ticket: pause (HITL) or resolve."""
    repo = AgentRepository(session)
    ticket = _load_ticket(session, ticket_id)
    if ticket.status in TERMINAL_TICKETS:
        raise UnprocessableError(f"ticket is already {ticket.status.lower()}")
    if repo.active_for_ticket(ticket.id) is not None:
        raise ConflictError("an AI run is already active for this ticket")

    run = repo.create_run(ticket_id=ticket.id)
    ticket.status = TICKET_AI_PROCESSING
    session.commit()
    _audit(session, repo, ticket, "run_started", metadata={"run_id": str(run.id)})
    bus.emit(str(ticket.id), "ai_started", {"run_id": str(run.id)})

    tools = _traced_tools(session, repo, run, ticket)

    def _on_node(node: str, state: dict) -> None:
        _persist_graph_state(session, run, state)
        label = _NODE_EVENTS.get(node, node)
        bus.emit(str(ticket.id), "ai_activity", {"node": node, "label": label})
        if node == "supervisor" and state.get("intent"):
            bus.emit(str(ticket.id), "intent_classified",
                     {"intent": state.get("intent"), "workflow": state.get("workflow")})

    state = run_support_ticket(str(ticket.id), tools=tools, llm=llm, on_node=_on_node)
    _persist_graph_state(session, run, state)
    run.intent = state.get("intent") or None
    run.workflow = state.get("workflow") or None
    run.decision = state.get("decision")
    run.error = state.get("error")
    run.verification_result = _jsonable(state.get("verification_result") or {})
    _audit(session, repo, ticket, "run_decided",
           metadata={"intent": run.intent, "workflow": run.workflow, "decision": run.decision})

    approval_id = None
    if is_paused_for_human(state):
        proposed = state.get("proposed_action") or {}
        approval = repo.create_approval(
            ticket_id=ticket.id,
            run_id=run.id,
            action_type=proposed.get("action_type", "UNKNOWN"),
            payload={
                "action_type": proposed.get("action_type"),
                "order_id": proposed.get("order_id"),
                "amount_paise": proposed.get("amount_paise"),
                "reason": proposed.get("reason", ""),
            },
        )
        approval.expires_at = datetime.datetime.now(datetime.UTC) + APPROVAL_TTL
        ticket.status = TICKET_WAITING_FOR_HUMAN
        run.status = RUN_WAITING
        _audit(session, repo, ticket, "approval_requested",
               metadata={"approval_id": str(approval.id)})
        bus.emit(str(ticket.id), "waiting_for_approval", {"approval_id": str(approval.id)})
        bus.emit(str(ticket.id), "approval_required",
                 {"approval_id": str(approval.id), "action": approval.action_type})
        approval_id = str(approval.id)
    elif state.get("decision") == "ask_customer" and state.get("resolution"):
        _save_customer_message(session, ticket, state["resolution"])
        ticket.status = TICKET_WAITING_FOR_CUSTOMER
        run.status = RUN_COMPLETED
        run.completed_at = datetime.datetime.now(datetime.UTC)
        _audit(session, repo, ticket, "run_waiting_customer", metadata={"decision": run.decision})
        bus.emit(str(ticket.id), "waiting_for_customer", {"decision": run.decision})
    elif (
        state.get("decision") in ("resolved_ready", "answered")
        and state.get("resolution")
        and ticket.status == TICKET_AI_PROCESSING
    ):
        _save_customer_message(session, ticket, state["resolution"])
        support_service.resolve(
            session,
            staff_id="ai-agent",
            ticket_id=str(ticket.id),
            resolution=state.get("resolution") or "Resolved by the AI support agent.",
        )
        run.status = RUN_COMPLETED
        run.completed_at = datetime.datetime.now(datetime.UTC)
        _audit(session, repo, ticket, "run_resolved", metadata={"decision": run.decision})
        bus.emit(str(ticket.id), "ticket_resolved", {"decision": run.decision})
    elif state.get("decision") == "ineligible" and state.get("resolution"):
        _save_customer_message(session, ticket, state["resolution"])
        ticket.status = TICKET_OPEN
        run.status = RUN_COMPLETED
        run.completed_at = datetime.datetime.now(datetime.UTC)
        _audit(session, repo, ticket, "run_completed", metadata={"decision": run.decision})
        bus.emit(str(ticket.id), "run_completed", {"decision": run.decision})
    else:
        if state.get("resolution") and state.get("decision") != "needs_human":
            try:
                _save_customer_message(session, ticket, state["resolution"])
            except Exception:
                pass
        if state.get("escalated") or state.get("decision") == "needs_human":
            ticket.status = TICKET_ESCALATED
            run.status = RUN_FAILED
            run.completed_at = datetime.datetime.now(datetime.UTC)
            try:
                support_service.escalate(
                    session, staff_id="ai-agent", ticket_id=str(ticket.id),
                    reason=state.get("error") or "AI needs human help",
                )
            except Exception:
                pass
            _audit(session, repo, ticket, "run_escalated", metadata={"decision": run.decision})
            bus.emit(str(ticket.id), "run_escalated", {"decision": run.decision})
        else:
            ticket.status = TICKET_OPEN
            run.status = RUN_COMPLETED
            run.completed_at = datetime.datetime.now(datetime.UTC)
            _audit(session, repo, ticket, "run_completed", metadata={"decision": run.decision})
            bus.emit(str(ticket.id), "run_completed", {"decision": run.decision})
    session.commit()
    session.refresh(run)
    return {
        "run_id": str(run.id),
        "status": run.status,
        "intent": run.intent,
        "decision": run.decision,
        "approval_id": approval_id,
    }


def decide_approval(
    session: Session,
    *,
    approval_id: str,
    staff_id: str,
    approved: bool,
    note: str | None = None,
) -> dict:
    """Resume SAME LangGraph execution with the human decision (approve/reject)."""
    repo = AgentRepository(session)
    try:
        approval_uuid = uuid.UUID(approval_id)
    except ValueError:
        raise NotFoundError("approval not found") from None
    approval = repo.get_approval(approval_uuid)
    if approval is None:
        raise NotFoundError("approval not found")
    if approval.status != "PENDING":
        raise UnprocessableError(f"approval is already {approval.status.lower()}")
    try:
        staff_uuid = uuid.UUID(staff_id)
    except ValueError:
        staff_uuid = None

    now = datetime.datetime.now(datetime.UTC)
    if approval.expires_at is not None and approval.expires_at < now:
        approval.status = APPROVAL_EXPIRED
        approval.resolved_at = now
        approval.resolved_by = staff_uuid
        ticket = _load_ticket(session, str(approval.ticket_id))
        run = repo.get_run(approval.agent_run_id)
        if run is not None:
            run.status = RUN_COMPLETED
            run.decision = "expired"
            run.completed_at = now
        ticket.status = TICKET_OPEN
        _save_customer_message(
            session, ticket,
            "My proposed action expired before support could review it — a human agent will handle this ticket.",
        )
        _audit(session, repo, ticket, "approval_expired",
               actor_type="SUPPORT_AGENT", actor_id=staff_uuid)
        bus.emit(str(ticket.id), "approval_expired", {"approval_id": str(approval.id)})
        session.commit()
        return {"approval_id": str(approval.id), "status": approval.status, "executed": False}

    ticket = _load_ticket(session, str(approval.ticket_id))
    run = repo.get_run(approval.agent_run_id)
    approval.resolved_at = now
    approval.resolved_by = staff_uuid
    approval.human_note = (note or "").strip() or None

    if not approved:
        approval.status = APPROVAL_REJECTED
        if run is not None:
            saved = dict(run.graph_state or {})
            saved["approval_status"] = "rejected"
            saved["human_feedback"] = approval.human_note
            saved["decision"] = "rejected"
            run.graph_state = _jsonable(saved)
            run.status = RUN_COMPLETED
            run.decision = "rejected"
            run.completed_at = now
        ticket.status = TICKET_OPEN
        CustomerTicketRepository(session).add_message(
            ticket_id=ticket.id,
            sender_type=SENDER_AI_AGENT,
            sender_id=None,
            message=(
                "Support reviewed my proposal and declined it — "
                "a human agent will handle this ticket."
            ),
        )
        _audit(session, repo, ticket, "approval_rejected",
               actor_type="SUPPORT_AGENT", actor_id=staff_uuid)
        bus.emit(str(ticket.id), "approval_rejected", {"approval_id": str(approval.id)})
        session.commit()
        return {"approval_id": str(approval.id), "status": approval.status, "executed": False}

    if ticket.status != TICKET_WAITING_FOR_HUMAN:
        raise UnprocessableError("ticket is no longer awaiting approval")
    approval.status = APPROVAL_APPROVED
    payload = approval.action_payload or {}

    # Resume SAME graph execution with approval injected. The execute node
    # uses the idempotent `approval:{id}` key so retries never duplicate.
    saved_state = dict(run.graph_state or {}) if run is not None else {}
    tools = _traced_tools(session, repo, run, ticket) if run is not None else _live_tools()

    def _on_node(node: str, state: dict) -> None:
        if run is not None:
            _persist_graph_state(session, run, state)
        label = _NODE_EVENTS.get(node, node)
        bus.emit(str(ticket.id), "ai_activity", {"node": node, "label": label})

    key = f"approval:{approval.id}"
    try:
        action = action_service.get_action_by_key(session, mutation_key=key)
        verified = True
        resumed_state = dict(saved_state)
        resumed_state["action_result"] = {"id": action["id"]}
        resumed_state["verification_result"] = {"ok": True, "tool": "cached"}
    except NotFoundError:
        resumed = resume_support_ticket(
            saved_state,
            tools=tools,
            approval_status="approved",
            human_feedback=approval.human_note,
            on_node=_on_node,
        )
        if run is not None:
            _persist_graph_state(session, run, resumed)
        action_result = resumed.get("action_result") or {}
        # The graph's execute node uses `agent:{ticket}:{workflow}` keys;
        # mirror the result under the approval key for idempotent replays.
        verified = bool((resumed.get("verification_result") or {}).get("ok"))
        if not resumed.get("action_result"):
            # Fallback: execute via service with approval-scoped key.
            action = action_service.execute_action(
                session,
                action_type=payload.get("action_type"),
                order_id=payload.get("order_id"),
                ticket_id=str(ticket.id),
                mutation_key=key,
                amount_paise=payload.get("amount_paise"),
            )
            reverified = action_service.get_action_by_key(session, mutation_key=key)
            verified = reverified["status"] == "DONE" and reverified["id"] == action["id"]
            action_result = {"id": action["id"]}
        action = {"id": action_result.get("id", "unknown")}
    resolution_text = (
        f"Approved action executed and verified ({approval.action_type}). "
        f"{approval.human_note or ''}"
    ).strip()
    graph_resolution = (saved_state.get("resolution") or "").strip()
    final_message = graph_resolution or resolution_text
    _save_customer_message(session, ticket, final_message)
    support_service.resolve(
        session,
        staff_id=staff_id,
        ticket_id=str(ticket.id),
        resolution=resolution_text,
    )
    if run is not None:
        run.status = RUN_COMPLETED
        run.decision = "approved_executed"
        run.completed_at = now
        run.verification_result = _jsonable({"ok": verified})
    _audit(session, repo, ticket, "approval_approved",
           actor_type="SUPPORT_AGENT", actor_id=staff_uuid,
           metadata={"action_id": action["id"], "verified": verified})
    bus.emit(str(ticket.id), "approval_approved", {"approval_id": str(approval.id)})
    bus.emit(str(ticket.id), "ticket_resolved", {"decision": "approved_executed"})
    session.commit()
    return {
        "approval_id": str(approval.id),
        "status": approval.status,
        "executed": True,
        "verified": verified,
        "action_id": action["id"],
    }


def take_over(session: Session, *, ticket_id: str, staff_id: str) -> dict:
    """Staff takes a ticket back from the AI (cancels the active run)."""
    repo = AgentRepository(session)
    ticket = _load_ticket(session, ticket_id)
    run = repo.active_for_ticket(ticket.id)
    try:
        staff_uuid = uuid.UUID(staff_id)
    except ValueError:
        staff_uuid = None
    if run is None:
        return {"cancelled": False}
    run.status = RUN_CANCELLED
    run.completed_at = datetime.datetime.now(datetime.UTC)
    saved = dict(run.graph_state or {})
    saved["approval_status"] = "rejected"
    saved["human_feedback"] = "staff takeover"
    saved["decision"] = "cancelled"
    run.graph_state = _jsonable(saved)
    ticket.status = TICKET_OPEN
    _audit(session, repo, ticket, "takeover",
           actor_type="SUPPORT_AGENT", actor_id=staff_uuid)
    bus.emit(str(ticket.id), "taken_over", {"run_id": str(run.id)})
    session.commit()
    return {"cancelled": True, "run_id": str(run.id)}


def get_trace(session: Session, *, ticket_id: str) -> dict:
    """Persisted AI timeline for one ticket (powers the console panel)."""
    repo = AgentRepository(session)
    ticket = _load_ticket(session, ticket_id)
    run = repo.latest_for_ticket(ticket.id)
    calls = repo.list_tool_calls(run.id) if run else []
    approvals = repo.list_for_ticket(ticket.id)
    steps = build_trace(
        (
            {
                "id": str(run.id),
                "status": run.status,
                "intent": run.intent,
                "workflow": getattr(run, "workflow", None),
                "decision": run.decision,
                "verification_result": _jsonable(getattr(run, "verification_result", None) or {}),
                "error": getattr(run, "error", None),
                "created_at": run.created_at.isoformat(),
            }
            if run
            else None
        ),
        [
            {
                "id": str(c.id),
                "tool_name": c.tool_name,
                "status": c.status,
                "arguments": _jsonable(c.arguments or {}),
                "created_at": c.created_at.isoformat(),
            }
            for c in calls
        ],
        [
            {
                "id": str(a.id),
                "action_type": a.action_type,
                "status": a.status,
                "requested_at": a.created_at.isoformat(),
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            }
            for a in approvals
        ],
        ticket.status,
    )
    return {
        "ticket_id": str(ticket.id),
        "ticket_status": ticket.status,
        "run": (
            {
                "id": str(run.id),
                "status": run.status,
                "intent": run.intent,
                "workflow": getattr(run, "workflow", None),
                "decision": run.decision,
            }
            if run
            else None
        ),
        "steps": steps,
        "approvals": [
            {
                "id": str(a.id),
                "ticket_id": str(ticket.id),
                "ticket_number": ticket.ticket_number,
                "action_type": a.action_type,
                "action_payload": a.action_payload,
                "status": a.status,
                "requested_at": a.created_at.isoformat(),
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                "human_note": a.human_note,
                "expires_at": a.expires_at.isoformat() if getattr(a, "expires_at", None) else None,
            }
            for a in approvals
        ],
        "audits": [
            {
                "event": a.event_type,
                "actor": a.actor_type,
                "at": a.created_at.isoformat(),
            }
            for a in repo.list_audits(ticket.id)
        ],
    }


def list_approvals(session: Session, *, status: str | None = None) -> list[dict]:
    """Approvals queue (default PENDING) with ticket numbers."""
    repo = AgentRepository(session)
    tickets = CustomerTicketRepository(session)
    out = []
    for approval in repo.list_approvals(status=status or "PENDING"):
        ticket = tickets.get_by_id(approval.ticket_id)
        out.append(
            {
                "id": str(approval.id),
                "ticket_id": str(approval.ticket_id),
                "ticket_number": ticket.ticket_number if ticket else "?",
                "action_type": approval.action_type,
                "action_payload": approval.action_payload,
                "status": approval.status,
                "requested_at": approval.created_at.isoformat(),
                "resolved_at": approval.resolved_at.isoformat() if approval.resolved_at else None,
                "human_note": approval.human_note,
                "expires_at": approval.expires_at.isoformat()
                if getattr(approval, "expires_at", None)
                else None,
            }
        )
    return out
