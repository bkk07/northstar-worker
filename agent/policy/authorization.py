"""Authorization: may the worker act alone? (P-* rules, plan §16).

First failure wins, in plan order: scope, ownership, duplicates, then
effect rules. ALLOW and HUMAN_APPROVAL both require every earlier check
to pass; BLOCK carries the deciding rule for the audit trail. Pure
functions of contract, action, and facts — the LLM is never consulted.
"""

import datetime
from dataclasses import dataclass

from agent.contract.action_validator import TOOL_META
from agent.contract.models import Contract
from agent.policy import eligibility, rules
from agent.policy.facts import Facts


@dataclass(frozen=True)
class Decision:
    """One deterministic authorization verdict."""

    outcome: str  # allow | human_approval | block
    rule_id: str
    reason: str


def evaluate(contract: Contract, action: dict, facts: Facts, today: datetime.date) -> Decision:
    """Authorize one proposed action (fail-closed on anything unknown)."""
    tool = action.get("tool", "") if isinstance(action, dict) else ""
    meta = TOOL_META.get(tool)
    if meta is None or not isinstance(action.get("params"), dict):
        return Decision("block", "P-FAIL-CLOSED", f"unknown action: {tool!r}")
    params = action["params"]

    scope = _check_scope(contract, tool, params)
    if scope is not None:
        return scope
    if _missing_submit_facts(contract, tool, facts):
        return Decision("block", "P-FAIL-CLOSED", "missing order or ticket facts")
    ownership = _check_ownership(contract, tool, facts)
    if ownership is not None:
        return ownership
    duplicate = _check_duplicate(tool, params, facts)
    if duplicate is not None:
        return duplicate

    if tool != "browser_submit":
        return Decision("allow", "P-CAP-001", f"{tool} is within contract scope")
    return _authorize_commit(contract, params, facts, today)


def _check_scope(contract: Contract, tool: str, params: dict) -> Decision | None:
    if tool == "browser_submit":
        effect = params.get("effect", "")
        match = next((e for e in contract.effects if e.effect == effect), None)
        if match is None:
            return Decision("block", "P-CAP-001", f"effect {effect!r} outside contract")
        if match.capability not in contract.capabilities:
            return Decision("block", "P-CAP-001", f"task lacks {match.capability!r}")
        return None
    meta = TOOL_META[tool]
    if meta.capability not in contract.capabilities:
        return Decision("block", "P-CAP-001", f"task lacks {meta.capability!r}")
    return None


def _missing_submit_facts(contract: Contract, tool: str, facts: Facts) -> bool:
    if tool != "browser_submit":
        return False
    if contract.order_id and not facts.order:
        return True
    return bool(contract.ticket_id and not facts.ticket)


def _check_ownership(contract: Contract, tool: str, facts: Facts) -> Decision | None:
    if tool != "browser_submit":
        return None
    seen = {}
    if contract.customer_id:
        seen["contract"] = contract.customer_id
    order_customer = facts.order.get("customer_id", "")
    if order_customer:
        seen["order"] = order_customer
    ticket_customer = facts.ticket.get("customer_id", "")
    if ticket_customer:
        seen["ticket"] = ticket_customer
    if len(set(seen.values())) > 1:
        detail = ", ".join(f"{src}={cid[:8]}" for src, cid in sorted(seen.items()))
        return Decision("block", "P-OWN-001", f"ownership mismatch: {detail}")
    return None


def _check_duplicate(tool: str, params: dict, facts: Facts) -> Decision | None:
    if tool != "browser_submit":
        return None
    effect = params.get("effect", "")
    if effect == "replacement.create" and facts.existing_replacement:
        return Decision("block", "P-DUP-001", "active replacement exists; reconcile instead")
    if effect == "refund.create":
        if facts.existing_refund:
            return Decision("block", "P-DUP-001", "active refund exists; reconcile instead")
        amount = params.get("amount_paise")
        ticket_id = params.get("ticket_id", "")
        for prior in facts.order_refunds:
            if prior.get("amount_paise") == amount and prior.get("ticket_id") != ticket_id:
                return Decision(
                    "block",
                    "P-DUP-001",
                    "same amount already refunded on this order; reconcile instead",
                )
    return None


def _authorize_commit(
    contract: Contract, params: dict, facts: Facts, today: datetime.date
) -> Decision:
    effect = params.get("effect", "")
    if effect == "replacement.create":
        return _authorize_replacement(params, facts, today)
    if effect == "refund.create":
        return _authorize_refund(params, facts)
    if effect in ("ticket.note", "ticket.status", "ticket.reply"):
        return _authorize_ticket_effect(contract, effect, params)
    return Decision("block", "P-FAIL-CLOSED", f"unknown effect: {effect!r}")


def _authorize_replacement(params: dict, facts: Facts, today: datetime.date) -> Decision:
    failed = eligibility.check_replacement(facts, params.get("order_item_id", ""), today)
    if failed is not None:
        rule_id, reason = failed
        return Decision("block", rule_id, reason)
    item = next(
        i for i in facts.order.get("items", []) if i.get("id") == params.get("order_item_id")
    )
    total = item.get("unit_paise", 0) * item.get("qty", 1)
    cap = facts.threshold("P-REPL-001", "max_paise", rules.REPL_AUTO_MAX_PAISE)
    if total <= cap:
        return Decision("allow", "P-REPL-001", f"eligible replacement totalling {total} paise")
    return Decision(
        "human_approval", "P-REPL-002", f"replacement totalling {total} paise needs approval"
    )


def _authorize_refund(params: dict, facts: Facts) -> Decision:
    amount = params.get("amount_paise", 0)
    failed = eligibility.check_refund(facts, amount)
    if failed is not None:
        rule_id, reason = failed
        if rule_id == "E-REF-001":
            return Decision("block", "P-REF-004", reason)
        return Decision("block", rule_id, reason)
    approval_max = facts.threshold("P-REF-003", "max_paise", rules.REF_APPROVAL_MAX_PAISE)
    if amount > approval_max:
        return Decision("block", "P-REF-004", f"refund {amount} paise above approval cap")
    if "refund_history" in facts.missing:
        return Decision("block", "P-FAIL-CLOSED", "refund history unreadable")
    max_count = facts.threshold("P-REF-001", "max_count_90d", rules.REF_MAX_COUNT_90D)
    auto_max = facts.threshold("P-REF-001", "max_paise", rules.REF_AUTO_MAX_PAISE)
    repeat_auto = facts.threshold(
        "P-REF-002", "repeat_auto_max_paise", rules.REF_REPEAT_AUTO_MAX_PAISE
    )
    if facts.refunds_last_90d > max_count:
        if amount <= repeat_auto:
            return Decision("allow", "P-REF-002", "repeat refunder within tiny-amount band")
        return Decision("human_approval", "P-REF-002", "repeat refunder needs approval")
    if amount <= auto_max:
        return Decision("allow", "P-REF-001", f"refund {amount} paise within auto band")
    return Decision("human_approval", "P-REF-003", f"refund {amount} paise needs approval")


def _authorize_ticket_effect(contract: Contract, effect: str, params: dict) -> Decision:
    if params.get("ticket_id", "") != (contract.ticket_id or ""):
        return Decision("block", "P-CAP-001", f"{effect} outside the contract ticket")
    return Decision("allow", "P-NOTE-001", f"{effect} on the contract's own ticket")
