"""Chat service: operator message -> assistant reply (+ optional task launch).

Deterministic intent handling over `parse_intent`; the only side effects are
task creation and the injected `start_run` hook (the runner itself runs in a
background thread via `chat_runner`). Chat text never approves, rejects, or
answers on anyone's behalf — those stay explicit button calls.
"""

from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.repositories.ops.ticket_repository import TicketRepository
from app.schemas.worker.chat import ChatAction, ChatReply
from app.schemas.worker.tasks import TaskCreate
from app.services.ops.ticket_service import OpsTicketService
from app.services.worker.chat_intent import ChatIntent, parse_intent
from app.services.worker.task_service import TaskService
from database.models.biz.order import Order

HELP_TEXT = (
    "I solve support tickets when you ask. Try:\n"
    "• “Solve ticket TCK-XXXX” — I create a task and run it, narrating here.\n"
    "• “Status of TCK-XXXX” — ticket state.\n"
    "• “Status of my last task” — where the run stands.\n"
    "• “Show open tickets” — the current queue.\n"
    "Approvals and answers always use the buttons on the task page — "
    "typed “yes” never counts."
)

APPROVE_REFUSAL = (
    "I can't approve or reject from chat — that's a safety rule, so a stray "
    "“yes” can never trigger a mutation. Open the task below and use the "
    "Approve / Reject buttons; the run resumes on its own."
)

_UNKNOWN_TICKET = "I can't find ticket {code}. Check the code, or ask me to “show open tickets”."


class ChatService:
    """Answer one chat message (session-per-request, like other services)."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._tasks = TaskService(session)
        self._tickets = TicketRepository(session)

    def reply(
        self, message: str, start_run: Callable[[str, str], None] | None = None
    ) -> ChatReply:
        """Route the message to its intent handler."""
        intent = parse_intent(message)
        if intent.kind == "solve_ticket":
            return self._solve(intent, start_run)
        if intent.kind == "ticket_status":
            return self._ticket_status(intent)
        if intent.kind == "task_status":
            return self._task_status(intent)
        if intent.kind == "list_tickets":
            return self._list_tickets()
        if intent.kind == "approve_attempt":
            return ChatReply(reply=APPROVE_REFUSAL)
        return ChatReply(reply=HELP_TEXT)

    def _solve(
        self, intent: ChatIntent, start_run: Callable[[str, str], None] | None
    ) -> ChatReply:
        """Create the task from the ticket and launch its run."""
        assert intent.ticket_code is not None
        ticket = self._tickets.get_by_code(intent.ticket_code)
        if ticket is None:
            return ChatReply(reply=_UNKNOWN_TICKET.format(code=intent.ticket_code))
        order_code = ""
        if ticket.order_id is not None:
            order = self._session.get(Order, ticket.order_id)
            if order is not None:
                order_code = f" on order {order.code}"
        body = (ticket.body or "").strip().replace("\n", " ")
        if len(body) > 200:
            body = body[:200].rstrip() + "…"
        task_text = (
            f"Handle {ticket.category} ticket {ticket.code}{order_code}: "
            f"{ticket.subject} — {body}".strip()
        )
        task = self._tasks.create_task(
            TaskCreate(text=task_text, mode="explicit"), created_by="chat"
        )
        if start_run is not None:
            start_run(str(task.id), task_text)
        short = str(task.id)[:8]
        return ChatReply(
            reply=(
                f"On it — solving {ticket.code} as task {short}. "
                "I'll narrate progress here; the run parks itself and asks "
                "if it needs a decision from you."
            ),
            task_id=task.id,
            actions=[
                ChatAction(
                    kind="task",
                    label=f"Open task {short}",
                    task_id=task.id,
                    href=f"/worker/tasks/{task.id}",
                )
            ],
        )

    def _ticket_status(self, intent: ChatIntent) -> ChatReply:
        """Summarize one ticket's state."""
        assert intent.ticket_code is not None
        ticket = self._tickets.get_by_code(intent.ticket_code)
        if ticket is None:
            return ChatReply(reply=_UNKNOWN_TICKET.format(code=intent.ticket_code))
        return ChatReply(
            reply=(
                f"{ticket.code} is {ticket.status} "
                f"({ticket.category}): {ticket.subject}."
            ),
            actions=[
                ChatAction(
                    kind="ticket",
                    label=f"Open {ticket.code}",
                    href=f"/ops/tickets/{ticket.code}",
                )
            ],
        )

    def _task_status(self, intent: ChatIntent) -> ChatReply:
        """Summarize one task's run state (or the newest task for “latest”)."""
        task_id = intent.ref
        try:
            if task_id == "latest":
                tasks = self._tasks.list_tasks(limit=1)
                if not tasks:
                    return ChatReply(reply="No tasks yet — ask me to solve a ticket.")
                task = tasks[0]
            else:
                assert task_id is not None
                task = self._tasks.get_task(UUID(task_id) if len(task_id) > 8 else self._resolve_prefix(task_id))
        except (NotFoundError, ValueError):
            return ChatReply(
                reply="I can't find that task. Ask me to solve a ticket, or check the dashboard."
            )
        state = task.status.split("_")
        return ChatReply(
            reply=(
                f"Task {str(task.id)[:8]} is {' '.join(state)}: “{task.text[:120]}”."
            ),
            task_id=task.id,
            actions=[
                ChatAction(
                    kind="task",
                    label="Open task",
                    task_id=task.id,
                    href=f"/worker/tasks/{task.id}",
                )
            ],
        )

    def _resolve_prefix(self, prefix: str) -> UUID:
        """Expand an 8-hex task prefix to its full id (404 when ambiguous)."""
        rows = self._tasks.list_tasks(limit=200)
        matches = [t for t in rows if str(t.id).startswith(prefix.lower())]
        if len(matches) != 1:
            raise NotFoundError(f"task {prefix} not found")
        return matches[0].id

    def _list_tickets(self) -> ChatReply:
        """List the first open tickets with their codes."""
        page = OpsTicketService(self._session).list_tickets(page=1, page_size=5)
        if page.total == 0:
            return ChatReply(reply="The queue is empty — nothing to solve right now.")
        lines = [f"• {item.code} — {item.status} — {item.subject}" for item in page.items]
        extra = f"\n…and {page.total - len(page.items)} more." if page.total > len(page.items) else ""
        return ChatReply(
            reply=f"Open tickets ({page.total}):\n" + "\n".join(lines) + extra + "\nSay “solve ticket TCK-…” and I'll take one.",
            actions=[
                ChatAction(kind="tickets", label="Open queue", href="/ops/tickets")
            ],
        )
