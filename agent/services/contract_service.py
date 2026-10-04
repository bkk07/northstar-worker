"""Contract service: interpretation + DB facts to a locked contract.

Resolution binds every human code in the operator text through read
tools: `C102` via customer search, `ORD-1942` / `TCK-101` via the shop
reads (code-addressable), names via search with multi-match flagged.
Ownership is cross-checked from DB facts — conflicts park for the
operator instead of binding a mixed triple.

Amounts are parsed from the operator text only (paise ints). Ticket or
page text never contributes an amount: the compiler's allowlist is built
here, from this function alone.
"""

import re
from collections.abc import Callable

from sqlalchemy.orm import Session

from agent.contract.compiler import compile_contract
from agent.contract.models import Contract, EntityResolution
from agent.llm.schemas import Interpretation
from agent.ports.tool_gateway import ToolGateway
from agent.repositories.contract_repository import ContractRepository
from agent.services.understanding_service import UnderstandingService

CUSTOMER_CODE = re.compile(r"\bC(\d{3,})\b")
ORDER_CODE = re.compile(r"\bORD-(\d+)\b", re.IGNORECASE)
TICKET_CODE = re.compile(r"\bTCK-([A-Za-z0-9-]+)\b", re.IGNORECASE)
MONEY = re.compile(r"(?:Rs\.?|₹|INR)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)


def parse_operator_amounts(task_text: str) -> list[int]:
    """Paise amounts stated by the operator (sorted, deduplicated)."""
    amounts = set()
    for match in MONEY.finditer(task_text):
        raw = match.group(1).replace(",", "")
        try:
            amounts.add(int(round(float(raw) * 100)))
        except ValueError:
            continue
    return sorted(amounts)


def extract_codes(task_text: str) -> dict[str, list[str]]:
    """Human codes in the operator text (deterministic, not LLM-proposed)."""
    normalize_order = {code.upper() for code in ORDER_CODE.findall(task_text)}
    return {
        "customers": [f"C{digits}" for digits in CUSTOMER_CODE.findall(task_text)],
        "orders": [f"ORD-{digits}" for digits in normalize_order],
        "tickets": [f"TCK-{suffix.upper()}" for suffix in TICKET_CODE.findall(task_text)],
    }


def resolve_entities(
    task_id: str,
    task_text: str,
    interpretation: Interpretation,
    gateway: ToolGateway,
) -> EntityResolution:
    """Bind customer/order/ticket from read-tool facts (no guessing)."""
    resolution = EntityResolution()
    codes = extract_codes(task_text)

    for code in codes["customers"]:
        _bind_customer_code(task_id, gateway, code, resolution)
    for name in interpretation.mentioned_names:
        _bind_customer_name(task_id, gateway, name, resolution)
    for code in codes["orders"]:
        _bind_order(task_id, gateway, code, resolution)
    for code in codes["tickets"]:
        _bind_ticket(task_id, gateway, code, resolution)
    _cross_check_ownership(resolution)
    return resolution


def _bind_customer_code(
    task_id: str, gateway: ToolGateway, code: str, resolution: EntityResolution
) -> None:
    try:
        found = gateway.search_customer(task_id, code).get("customers", [])
    except Exception:
        resolution.ambiguities.append(f"customer lookup failed for {code}")
        return
    exact = [c for c in found if c.get("code") == code]
    if not exact:
        resolution.unmatched_codes.append(code)
    elif resolution.customer is None:
        customer = exact[0]
        resolution.customer = {
            "id": customer["id"],
            "code": customer["code"],
            "name": customer.get("name", ""),
        }
    elif resolution.customer.get("code") != code:
        resolution.ambiguities.append(
            f"conflicting customers: {resolution.customer.get('code')} vs {code}"
        )


def _bind_customer_name(
    task_id: str, gateway: ToolGateway, name: str, resolution: EntityResolution
) -> None:
    if resolution.customer is not None:
        return
    try:
        found = gateway.search_customer(task_id, name).get("customers", [])
    except Exception:
        resolution.ambiguities.append(f"customer lookup failed for {name!r}")
        return
    if not found:
        resolution.ambiguities.append(f"no customer matches {name!r}")
    elif len(found) == 1:
        customer = found[0]
        resolution.customer = {
            "id": customer["id"],
            "code": customer["code"],
            "name": customer.get("name", ""),
        }
    else:
        codes = sorted({c.get("code", "?") for c in found})
        resolution.ambiguities.append(
            f"multiple customers match {name!r}: {', '.join(codes)} — which one?"
        )


def _bind_order(
    task_id: str, gateway: ToolGateway, code: str, resolution: EntityResolution
) -> None:
    try:
        order = gateway.api_get(task_id, f"/api/shop/orders/{code}").get("result", {})
    except Exception:
        resolution.unmatched_codes.append(code)
        return
    if not order or not order.get("id"):
        resolution.unmatched_codes.append(code)
        return
    if resolution.order is None:
        resolution.order = {
            "id": order["id"],
            "code": order.get("code", code),
            "customer_id": order.get("customer_id", ""),
            "items": [
                {"id": item["id"], "title": item.get("title", ""), "sku": item.get("sku", "")}
                for item in order.get("items", [])
            ],
        }
    elif resolution.order.get("code") != order.get("code", code):
        resolution.ambiguities.append("task mentions more than one order")
    _bind_customer_from_order(task_id, gateway, resolution)


def _bind_customer_from_order(
    task_id: str, gateway: ToolGateway, resolution: EntityResolution
) -> None:
    """The order's own customer is a DB fact — bind it when unbound."""
    customer_id = (resolution.order or {}).get("customer_id", "")
    if resolution.customer is not None or not customer_id:
        return
    try:
        customer = gateway.get_customer(task_id, customer_id).get("customer", {})
    except Exception:
        return
    if customer.get("id"):
        resolution.customer = {
            "id": customer["id"],
            "code": customer.get("code", ""),
            "name": customer.get("name", ""),
        }


def _bind_ticket(
    task_id: str, gateway: ToolGateway, code: str, resolution: EntityResolution
) -> None:
    try:
        ticket = gateway.api_get(task_id, f"/api/shop/tickets/{code}").get("result", {})
    except Exception:
        resolution.unmatched_codes.append(code)
        return
    if not ticket or not ticket.get("id"):
        resolution.unmatched_codes.append(code)
        return
    if resolution.ticket is None:
        resolution.ticket = {
            "id": ticket["id"],
            "code": ticket.get("code", code),
            "customer_id": ticket.get("customer_id", ""),
            "order_id": ticket.get("order_id", ""),
        }
    elif resolution.ticket.get("code") != ticket.get("code", code):
        resolution.ambiguities.append("task mentions more than one ticket")


def _cross_check_ownership(resolution: EntityResolution) -> None:
    """Bound triples must agree; conflicts park instead of mixing."""
    customer_id = (resolution.customer or {}).get("id", "")
    order_customer = (resolution.order or {}).get("customer_id", "")
    ticket_customer = (resolution.ticket or {}).get("customer_id", "")
    ticket_order = (resolution.ticket or {}).get("order_id", "")
    order_id = (resolution.order or {}).get("id", "")
    problems = []
    if customer_id and order_customer and customer_id != order_customer:
        problems.append("order belongs to a different customer")
    if customer_id and ticket_customer and customer_id != ticket_customer:
        problems.append("ticket belongs to a different customer")
    if order_id and ticket_order and order_id != ticket_order:
        problems.append("ticket is filed on a different order")
    resolution.ambiguities.extend(f"ownership mismatch: {p}" for p in problems)


class ContractService:
    """Build and lock task contracts (understanding + resolution + compile)."""

    def __init__(
        self,
        understanding: UnderstandingService,
        gateway: ToolGateway,
        session_factory: Callable[[], Session],
    ) -> None:
        self._understanding = understanding
        self._gateway = gateway
        self._sessions = session_factory

    def build_contract(self, task_id: str, task_text: str) -> Contract:
        """Interpret, resolve, compile, and persist one contract."""
        interpretation = self._understanding.interpret(task_text)
        resolution = resolve_entities(task_id, task_text, interpretation, self._gateway)
        contract = compile_contract(
            task_id, task_text, interpretation, resolution, parse_operator_amounts(task_text)
        )
        session = self._sessions()
        try:
            ContractRepository(session).save(contract)
            session.commit()
        finally:
            session.close()
        return contract
