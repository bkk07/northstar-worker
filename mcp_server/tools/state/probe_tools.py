"""Probe tool: committed-state reads for probe-before-retry (Phase 19)."""

from mcp_server import context
from mcp_server.schemas.tools import InspectStateInput


def inspect_state(task_id: str, kind: str, key: str, extra: dict | None = None) -> dict:
    """Probe state without side effects.

    kinds: `mutation` (idempotency key), `replacement` (order_item_id),
    `refund` (ticket_id + extra.order_id). Unknown kinds are rejected.
    """
    args = InspectStateInput(task_id=task_id, kind=kind, key=key, extra=extra or {})
    context.store().check(args.task_id, "probe")
    reader = context.reader()
    if args.kind == "mutation":
        return reader.probe_mutation(args.key)
    if args.kind == "replacement":
        return reader.probe_replacement(args.key)
    if args.kind == "refund":
        order_id = args.extra.get("order_id", "")
        if not order_id:
            raise ValueError("inspect_state refund needs extra.order_id")
        return reader.probe_refund(args.key, order_id)
    raise ValueError(f"unknown probe kind: {args.kind}")
