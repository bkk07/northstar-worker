"""Read tools: customers and orders (side-effect free)."""

from mcp_server import context
from mcp_server.schemas.tools import (
    GetCustomerInput,
    GetOrderInput,
    SearchCustomerInput,
    SearchOrderInput,
)


def search_customer(task_id: str, q: str) -> dict:
    """Find customers by name, email, or code (empty and multi-match are data)."""
    args = SearchCustomerInput(task_id=task_id, q=q)
    context.store().check(args.task_id, "read")
    return {"customers": context.reader().search_customers(args.q)}


def get_customer(task_id: str, customer_id: str) -> dict:
    """One customer by UUID (missing → not_found error)."""
    args = GetCustomerInput(task_id=task_id, customer_id=customer_id)
    context.store().check(args.task_id, "read")
    return {"customer": context.reader().get_customer(args.customer_id)}


def search_order(task_id: str, customer_id: str, q: str = "") -> dict:
    """Orders of one customer, optionally filtered by code fragment."""
    args = SearchOrderInput(task_id=task_id, customer_id=customer_id, q=q)
    context.store().check(args.task_id, "read")
    return {"orders": context.reader().search_orders(args.customer_id, args.q)}


def get_order(task_id: str, order_id: str) -> dict:
    """One order with items (missing → not_found error)."""
    args = GetOrderInput(task_id=task_id, order_id=order_id)
    context.store().check(args.task_id, "read")
    return {"order": context.reader().get_order(args.order_id)}
