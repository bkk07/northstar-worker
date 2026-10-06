"""Chat intent parser: deterministic, no model calls.

Recognizes ticket codes (`TCK-...`), task ids (uuid or 8-hex prefix), and a
small verb vocabulary. Anything unrecognized is `unknown` so the service can
answer with the help text. Pure functions — unit-tested without a database.
"""

import re
from dataclasses import dataclass

TICKET_RE = re.compile(r"\bTCK-[A-Z0-9]{3,}\b", re.IGNORECASE)
ORDER_RE = re.compile(r"\bORD-[A-Z0-9]{3,}\b", re.IGNORECASE)
SKU_RE = re.compile(r"\b(?!ORD-|TCK-)[A-Z]{2,4}-[0-9]{2}[A-Z0-9]*\b")
UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE
)
SHORT_ID_RE = re.compile(r"\btask\s+([0-9a-f]{8})\b", re.IGNORECASE)

_SOLVE_RE = re.compile(r"\b(solve|handle|fix|work on|take care of|resolve|do)\b", re.IGNORECASE)
_STATUS_RE = re.compile(r"\bstatus\b", re.IGNORECASE)
_LIST_RE = re.compile(r"\b(list|show|what|which)\b", re.IGNORECASE)
_APPROVE_RE = re.compile(
    r"\b(approve|approved|reject|rejected|\byes\b|\bno\b|confirm it|go ahead)\b", re.IGNORECASE
)
_HELP_RE = re.compile(r"\b(help|what can you do|how do|example|examples)\b", re.IGNORECASE)
_LATEST_RE = re.compile(r"\b(last|latest|my|current)\b", re.IGNORECASE)
_DETAIL_RE = re.compile(
    r"\b(detail|details|about|tell me|show me|info|information|order|product|products|policy|policies)\b",
    re.IGNORECASE,
)
_APPROVALS_RE = re.compile(
    r"\b(pending approvals?|waiting( for)? approval|needs? my (approval|decision)|"
    r"anything waiting|my approvals?|approval queue)\b",
    re.IGNORECASE,
)
_POLICY_RE = re.compile(r"\bpolic(y|ies|y rules?)\b", re.IGNORECASE)
_REFUND_POLICY_RE = re.compile(r"\brefund polic", re.IGNORECASE)


@dataclass(frozen=True)
class ChatIntent:
    """Parsed operator intent (kind + optional ticket/order/task reference)."""

    kind: str
    ticket_code: str | None = None
    ref: str | None = None
    order_code: str | None = None
    sku: str | None = None


def parse_intent(message: str) -> ChatIntent:
    """Classify one chat message into a `ChatIntent`."""
    text = message.strip()
    ticket_match = TICKET_RE.search(text)
    ticket_code = ticket_match.group(0).upper() if ticket_match else None
    order_match = ORDER_RE.search(text)
    order_code = order_match.group(0).upper() if order_match else None
    sku_match = SKU_RE.search(text)
    sku = sku_match.group(0).upper() if sku_match else None
    uuid_match = UUID_RE.search(text)
    short_match = SHORT_ID_RE.search(text)
    task_ref = uuid_match.group(0) if uuid_match else (short_match.group(1) if short_match else None)

    if _APPROVE_RE.search(text) and not ticket_code and not task_ref:
        return ChatIntent(kind="approve_attempt")
    if _HELP_RE.search(text):
        return ChatIntent(kind="help")
    if ticket_code and _SOLVE_RE.search(text):
        return ChatIntent(kind="solve_ticket", ticket_code=ticket_code)
    if _APPROVALS_RE.search(text):
        return ChatIntent(kind="approvals_list")
    if _STATUS_RE.search(text) or (_LATEST_RE.search(text) and task_ref):
        if task_ref:
            return ChatIntent(kind="task_status", ref=task_ref)
        if ticket_code:
            return ChatIntent(kind="ticket_status", ticket_code=ticket_code)
        if _LATEST_RE.search(text):
            return ChatIntent(kind="task_status", ref="latest")
    if _LATEST_RE.search(text) and re.search(r"\btask\b", text, re.IGNORECASE):
        return ChatIntent(kind="task_status", ref="latest")
    if ticket_code and _DETAIL_RE.search(text):
        return ChatIntent(kind="ticket_detail", ticket_code=ticket_code)
    if ticket_code and not _SOLVE_RE.search(text) and len(text) < 40:
        return ChatIntent(kind="ticket_status", ticket_code=ticket_code)
    if task_ref and not order_code and not sku:
        return ChatIntent(kind="task_status", ref=task_ref)
    if order_code:
        return ChatIntent(kind="order_detail", order_code=order_code)
    if sku:
        return ChatIntent(kind="product_detail", sku=sku)
    if _REFUND_POLICY_RE.search(text) or _POLICY_RE.search(text):
        return ChatIntent(kind="policy_answer")
    if _LIST_RE.search(text) and re.search(r"\btickets?\b", text, re.IGNORECASE):
        return ChatIntent(kind="list_tickets")
    if re.search(r"\bopen tickets\b", text, re.IGNORECASE):
        return ChatIntent(kind="list_tickets")
    if task_ref:
        return ChatIntent(kind="task_status", ref=task_ref)
    return ChatIntent(kind="unknown")
