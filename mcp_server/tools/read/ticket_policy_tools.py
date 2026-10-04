"""Read tools: tickets, policies, and the allowlisted GET fallback."""

from mcp_server import context
from mcp_server.schemas.tools import ApiGetInput, GetPolicyInput, GetTicketInput


def get_ticket(task_id: str, ticket_id: str) -> dict:
    """One ticket by UUID (missing → not_found error)."""
    args = GetTicketInput(task_id=task_id, ticket_id=ticket_id)
    context.store().check(args.task_id, "read")
    return {"ticket": context.reader().get_ticket(args.ticket_id)}


def get_policy(task_id: str, rule_key: str) -> dict:
    """One policy rule by key (missing → not_found error)."""
    args = GetPolicyInput(task_id=task_id, rule_key=rule_key)
    context.store().check(args.task_id, "read")
    return {"policy": context.reader().get_policy(args.rule_key)}


def api_get(task_id: str, path: str, params: dict | None = None) -> dict:
    """Fallback GET against an allowlisted read path (else rejected)."""
    args = ApiGetInput(task_id=task_id, path=path, params=params or {})
    context.store().check(args.task_id, "read.fallback")
    return {"result": context.reader().api_get(args.path, args.params)}
