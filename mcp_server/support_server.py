"""Support MCP server (spec Phase 7): business capabilities as clean tools.

Separate from the task/browser plane (`mcp_server.server`, :8002): these
24 tools operate on the Phase 2-6 domain (users, shop orders, catalog,
policies, mock actions, customer tickets, knowledge) by calling the same
backend service layer as the REST API — the LLM never gets raw SQL.

Run locally:
  PYTHONPATH=common;backend;database python -m mcp_server.support_server
Serve port: `SUPPORT_MCP_PORT` (default 8003).

Manual check with the MCP inspector:
  npx @modelcontextprotocol/inspector --cli http://127.0.0.1:8003/sse --method tools/list
"""

import os

from mcp.server.fastmcp import FastMCP

from mcp_server.support import (
    action_tools,
    knowledge_tools,
    order_tools,
    policy_tools,
    product_tools,
    ticket_tools,
    user_tools,
)

mcp = FastMCP(
    "northstar-support",
    host="127.0.0.1",
    port=int(os.environ.get("SUPPORT_MCP_PORT", "8003")),
)


# USER
@mcp.tool()
def get_user(user_id: str) -> dict:
    """Customer profile with order/ticket counts."""
    return user_tools.get_user(user_id)


@mcp.tool()
def get_user_orders(user_id: str) -> dict:
    """Order summaries for one customer, newest first."""
    return user_tools.get_user_orders(user_id)


@mcp.tool()
def get_user_tickets(user_id: str) -> dict:
    """Ticket summaries for one customer, newest first."""
    return user_tools.get_user_tickets(user_id)


# ORDER
@mcp.tool()
def get_order(order_id: str) -> dict:
    """Full order with items, payment, and live timeline."""
    return order_tools.get_order(order_id)


@mcp.tool()
def get_order_items(order_id: str) -> dict:
    """Order lines with product snapshots."""
    return order_tools.get_order_items(order_id)


@mcp.tool()
def get_order_status(order_id: str) -> dict:
    """Stored vs live lifecycle status for verification."""
    return order_tools.get_order_status(order_id)


@mcp.tool()
def get_order_tracking(order_id: str) -> dict:
    """Delivery timeline plus estimate."""
    return order_tools.get_order_tracking(order_id)


# PRODUCT
@mcp.tool()
def get_product(product_id: str) -> dict:
    """Product card data by id."""
    return product_tools.get_product(product_id)


@mcp.tool()
def get_product_details(product_id: str) -> dict:
    """Full product detail with policy summary."""
    return product_tools.get_product_details(product_id)


@mcp.tool()
def get_product_policy(product_id: str) -> dict:
    """Every policy flag for one product, plus the one-line summary."""
    return product_tools.get_product_policy(product_id)


# POLICY
@mcp.tool()
def check_refund_eligibility(order_id: str) -> dict:
    """Can this order be (further) refunded under policy?"""
    return policy_tools.check_refund_eligibility(order_id)


@mcp.tool()
def check_return_eligibility(order_id: str) -> dict:
    """Can this order be returned under policy?"""
    return policy_tools.check_return_eligibility(order_id)


@mcp.tool()
def check_replacement_eligibility(order_id: str) -> dict:
    """Can this order get a replacement under policy?"""
    return policy_tools.check_replacement_eligibility(order_id)


@mcp.tool()
def check_cancellation_eligibility(order_id: str) -> dict:
    """Can this order still be cancelled?"""
    return policy_tools.check_cancellation_eligibility(order_id)


# ACTIONS
@mcp.tool()
def mock_refund(
    order_id: str,
    mutation_key: str,
    ticket_id: str | None = None,
    amount_paise: int | None = None,
) -> dict:
    """Record a mock refund against a paid order (idempotent by mutation key)."""
    return action_tools.mock_refund(order_id, mutation_key, ticket_id, amount_paise)


@mcp.tool()
def mock_return(order_id: str, mutation_key: str, ticket_id: str | None = None) -> dict:
    """Record a mock return and mark the order RETURNED (idempotent)."""
    return action_tools.mock_return(order_id, mutation_key, ticket_id)


@mcp.tool()
def mock_replace(order_id: str, mutation_key: str, ticket_id: str | None = None) -> dict:
    """Record a mock replacement for a delivered order (idempotent)."""
    return action_tools.mock_replace(order_id, mutation_key, ticket_id)


@mcp.tool()
def mock_cancel_order(
    order_id: str, mutation_key: str, ticket_id: str | None = None
) -> dict:
    """Cancel a PROCESSING order (idempotent by mutation key)."""
    return action_tools.mock_cancel_order(order_id, mutation_key, ticket_id)


# TICKET
@mcp.tool()
def get_ticket(ticket_id: str) -> dict:
    """Full ticket context: conversation, customer, order, policies."""
    return ticket_tools.get_ticket(ticket_id)


@mcp.tool()
def add_ticket_message(
    ticket_id: str, message: str, sender_type: str = "AI_AGENT"
) -> dict:
    """Post an agent/staff/system message (terminal tickets reject)."""
    return ticket_tools.add_ticket_message(ticket_id, message, sender_type)


@mcp.tool()
def update_ticket(
    ticket_id: str, priority: str | None = None, category: str | None = None
) -> dict:
    """Change priority and/or category (the only agent-mutable fields)."""
    return ticket_tools.update_ticket(ticket_id, priority, category)


@mcp.tool()
def resolve_ticket(ticket_id: str, resolution: str) -> dict:
    """Resolve with a resolution note (terminal tickets reject)."""
    return ticket_tools.resolve_ticket(ticket_id, resolution)


@mcp.tool()
def escalate_ticket(ticket_id: str, reason: str | None = None) -> dict:
    """Escalate an actionable ticket, optional reason."""
    return ticket_tools.escalate_ticket(ticket_id, reason)


# KNOWLEDGE
@mcp.tool()
def search_knowledge(query: str, limit: int = 10) -> dict:
    """Substring search over products, product policies, and policy rules."""
    return knowledge_tools.search_knowledge(query, limit)


def main() -> None:
    """Serve SSE for agent clients."""
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
