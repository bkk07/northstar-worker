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
from app.schemas.worker.approvals import ApprovalRead
from app.schemas.worker.chat import ChatAction, ChatReply
from app.schemas.worker.tasks import TaskCreate
from app.services.commerce.catalog_service import CatalogService, rupees
from app.services.commerce.shop_service import ShopService
from app.services.ops.ticket_service import OpsTicketService
from app.services.worker.approval_service import ApprovalService
from app.services.worker.chat_intent import ChatIntent, parse_intent
from app.services.worker.chat_narrator import narrate
from app.services.worker.task_service import TaskService
from database.models.biz.order import Order

HELP_TEXT = (
    "I'm the support bot — ask me anything about tickets, orders, products, "
    "and policies, or hand me work. Try:\n"
    "• “Solve ticket TCK-XXXX” — I create a task and run it, narrating here.\n"
    "• “Tell me about TCK-XXXX” — ticket, order, products, and policies.\n"
    "• “Show order ORD-XXXX” / “Policy for HP-01” / “What's the refund policy?”\n"
    "• “Show open tickets” / “Anything waiting for approval?”\n"
    "Decisions always use the Approve / Reject buttons — typed “yes” never counts."
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
        self._shop = ShopService(session)
        self._catalog = CatalogService(session)
        self._approvals = ApprovalService(session)

    def reply(
        self, message: str, start_run: Callable[[str, str], None] | None = None
    ) -> ChatReply:
        """Route the message to its intent handler (model-phrased reply)."""
        intent = parse_intent(message)
        if intent.kind == "approve_attempt":
            # Safety text stays byte-exact — never model-phrased.
            return ChatReply(reply=APPROVE_REFUSAL)
        result = self._route(intent, start_run)
        return ChatReply(
            reply=narrate(message, result.reply),
            task_id=result.task_id,
            actions=result.actions,
        )

    def _route(
        self, intent: ChatIntent, start_run: Callable[[str, str], None] | None
    ) -> ChatReply:
        """Deterministic intent handling (draft replies + side effects)."""
        if intent.kind == "solve_ticket":
            return self._solve(intent, start_run)
        if intent.kind == "ticket_status":
            return self._ticket_status(intent)
        if intent.kind == "ticket_detail":
            return self._ticket_detail(intent)
        if intent.kind == "order_detail":
            return self._order_detail(intent)
        if intent.kind == "product_detail":
            return self._product_detail(intent)
        if intent.kind == "policy_answer":
            return self._policy_answer()
        if intent.kind == "approvals_list":
            return self._approvals_list()
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

    def _ticket_detail(self, intent: ChatIntent) -> ChatReply:
        """Ticket + linked order, products, and governing policies."""
        assert intent.ticket_code is not None
        ticket = self._tickets.get_by_code(intent.ticket_code)
        if ticket is None:
            return ChatReply(reply=_UNKNOWN_TICKET.format(code=intent.ticket_code))
        lines = [
            f"{ticket.code} is {ticket.status} ({ticket.category}): {ticket.subject}."
        ]
        actions = [
            ChatAction(
                kind="solve",
                label=f"Solve {ticket.code}",
                href=f"/worker/assistant?solve={ticket.code}",
            ),
            ChatAction(
                kind="ticket",
                label=f"Open {ticket.code}",
                href=f"/ops/tickets/{ticket.code}",
            ),
        ]
        if ticket.order_id is not None:
            order = self._session.get(Order, ticket.order_id)
            if order is not None:
                try:
                    detail = self._shop.get_order(order.code)
                except NotFoundError:
                    detail = None
                if detail is not None:
                    items = ", ".join(
                        f"{item.title} ({item.sku})" for item in detail.items
                    ) or "no items"
                    lines.append(
                        f"Order {detail.code} is {detail.status} — "
                        f"{rupees(detail.total_paise)} total, items: {items}."
                    )
                    policies = self._catalog.list_policies()
                    refund = next(
                        (p for p in policies if p.rule_key == "P-REF-001"), None
                    )
                    if refund is not None:
                        lines.append(f"Refund policy: {refund.summary}.")
                    actions.append(
                        ChatAction(
                            kind="order",
                            label=f"Open {detail.code}",
                            href=f"/shop/orders/{detail.code}",
                        )
                    )
        lines.append(f"Say “solve ticket {ticket.code}” and I'll take it.")
        return ChatReply(reply="\n".join(lines), actions=actions)

    def _order_detail(self, intent: ChatIntent) -> ChatReply:
        """Order state with its items and per-item policy pointers."""
        assert intent.order_code is not None
        try:
            order = self._shop.get_order(intent.order_code)
        except NotFoundError:
            return ChatReply(
                reply=f"I can't find order {intent.order_code}. Check the code."
            )
        items = "\n".join(
            f"• {item.title} ({item.sku}) ×{item.qty} — {rupees(item.unit_paise)}"
            for item in order.items
        ) or "• no items"
        actions = [
            ChatAction(
                kind="order",
                label=f"Open {order.code}",
                href=f"/shop/orders/{order.code}",
            )
        ]
        for item in order.items[:3]:
            actions.append(
                ChatAction(
                    kind="product",
                    label=f"Policy for {item.sku}",
                    href=f"/worker/assistant?product={item.sku}",
                )
            )
        return ChatReply(
            reply=(
                f"Order {order.code} is {order.status} — "
                f"{rupees(order.paid_paise)} paid of {rupees(order.total_paise)}.\n"
                f"{items}"
            ),
            actions=actions,
        )

    def _product_detail(self, intent: ChatIntent) -> ChatReply:
        """Product with the policies that apply to it."""
        assert intent.sku is not None
        try:
            detail = self._catalog.get_product(intent.sku)
        except NotFoundError:
            return ChatReply(
                reply=f"I don't carry {intent.sku}. Ask me to show open tickets instead."
            )
        product = detail.product
        top = detail.policies[:4]
        lines = [
            f"{product.title} ({product.sku}) — {product.category}, "
            f"{rupees(product.unit_paise)}."
        ]
        lines.extend(f"• {policy.summary}" for policy in top)
        return ChatReply(
            reply="\n".join(lines),
            actions=[
                ChatAction(
                    kind="policies",
                    label="All policies",
                    href="/worker/assistant?policies=1",
                )
            ],
        )

    def _policy_answer(self) -> ChatReply:
        """Headline refund/replacement policies."""
        policies = {p.rule_key: p for p in self._catalog.list_policies()}
        lines = ["Here's the refund policy at a glance:"]
        for key in ("P-REF-001", "P-REF-003", "E-REF-001", "E-REF-002", "P-REPL-001"):
            policy = policies.get(key)
            if policy is not None:
                lines.append(f"• {policy.summary} [{policy.rule_key}]")
        return ChatReply(reply="\n".join(lines))

    def _approvals_list(self) -> ChatReply:
        """Pending approvals with inline decision buttons."""
        pending = self._approvals.list_pending()[:5]
        if not pending:
            return ChatReply(reply="Nothing is waiting for approval right now.")
        lines = ["These need your decision:"]
        actions: list[ChatAction] = []
        for approval in pending:
            lines.append(
                f"• Task {str(approval.task_id)[:8]} wants to "
                f"{approval.requested_action}: {approval.reason}"
            )
            actions.extend(self._approval_actions(approval))
        return ChatReply(reply="\n".join(lines), actions=actions)

    @staticmethod
    def _approval_actions(approval: ApprovalRead) -> list[ChatAction]:
        """Inline Approve/Reject buttons bound to one approval id."""
        short = str(approval.task_id)[:8]
        return [
            ChatAction(
                kind="approval",
                label=f"Approve ({short})",
                task_id=approval.task_id,
                approval_id=approval.id,
                decision="approve",
            ),
            ChatAction(
                kind="approval",
                label=f"Reject ({short})",
                task_id=approval.task_id,
                approval_id=approval.id,
                decision="reject",
            ),
        ]

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
        actions = [
            ChatAction(
                kind="task",
                label="Open task",
                task_id=task.id,
                href=f"/worker/tasks/{task.id}",
            )
        ]
        if task.status in ("waiting_for_approval", "waiting_for_clarification"):
            for approval in self._approvals.list_pending():
                if approval.task_id == task.id:
                    actions.extend(self._approval_actions(approval))
        return ChatReply(
            reply=(
                f"Task {str(task.id)[:8]} is {' '.join(state)}: “{task.text[:120]}”."
            ),
            task_id=task.id,
            actions=actions,
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
