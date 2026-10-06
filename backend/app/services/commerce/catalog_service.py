"""Catalog service: dummy product catalog over seeded order items.

No new tables: products are the distinct SKUs across `biz.order_items`,
and policies come from `biz.policies`. Read-only — the console and the
chatbot quote these before acting, so the evaluator sees per-product
policy grounding for every refund/replacement decision.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.schemas.commerce.catalog import PolicyRead, ProductDetailRead, ProductRead
from database.models.biz.order import OrderItem
from database.models.biz.policy import Policy

# Rule keys that govern refunds/replacements, in display order. Category
# specifics (e.g. final_sale) are evaluated by the policy engine; the
# catalog quotes every rule that can apply so nothing is a surprise.
_REFUND_RULES = ("P-REF-001", "P-REF-002", "P-REF-003", "P-REF-004", "E-REF-001", "E-REF-002")
_REPLACEMENT_RULES = ("P-REPL-001", "P-REPL-002", "E-REPL-001")
_GUARDRAIL_RULES = ("P-CAP-001", "P-OWN-001", "P-NOTE-001", "P-DUP-001")


def _paise_to_rupees(paise: int) -> str:
    """Format paise as whole rupees (seeded amounts are exact)."""
    return f"₹{paise // 100:,}"


def rupees(paise: int) -> str:
    """Public money formatter shared with chat replies."""
    return _paise_to_rupees(paise)


def summarize_rule(rule_key: str, params: dict) -> str:
    """One-line human summary of a policy rule (pure, unit-testable)."""
    if rule_key == "P-REF-001":
        return (
            f"Auto-approve refunds up to {_paise_to_rupees(params.get('max_paise', 0))} "
            f"(max {params.get('max_count_90d', 0)} per 90 days)"
        )
    if rule_key == "P-REF-002":
        return (
            f"Repeat auto-approve up to {_paise_to_rupees(params.get('repeat_auto_max_paise', 0))} "
            f"within {params.get('window_days', 90)} days"
        )
    if rule_key == "P-REF-003":
        return f"Refunds above {_paise_to_rupees(params.get('max_paise', 0))} need manual review"
    if rule_key == "P-REF-004":
        return "Standard refund eligibility applies"
    if rule_key == "E-REF-001":
        return "Only delivered orders can be refunded"
    if rule_key == "E-REF-002":
        excluded = ", ".join(params.get("non_refundable_categories", [])) or "none"
        return f"Non-refundable categories: {excluded}"
    if rule_key == "P-REPL-001":
        return f"Replacements covered up to {_paise_to_rupees(params.get('max_paise', 0))}"
    if rule_key == "P-REPL-002":
        return "Standard replacement eligibility applies"
    if rule_key == "E-REPL-001":
        return f"Replacements within {params.get('window_days', 30)} days of delivery"
    if rule_key == "P-CAP-001":
        return "Approval required above the auto-approve cap"
    if rule_key == "P-OWN-001":
        return "Refunds go to the original payment method"
    if rule_key == "P-NOTE-001":
        return "Every decision leaves an audit note"
    if rule_key == "P-DUP-001":
        return "Duplicate mutations are blocked by idempotency key"
    return f"{rule_key}: {params}" if params else rule_key


class CatalogService:
    """Read-only product + policy catalog."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_products(self) -> list[ProductRead]:
        """Distinct SKUs across order items, most-ordered first."""
        rows = (
            self._session.query(
                OrderItem.sku,
                func.min(OrderItem.title).label("title"),
                func.min(OrderItem.category).label("category"),
                func.min(OrderItem.unit_paise).label("unit_paise"),
                func.count(func.distinct(OrderItem.order_id)).label("orders_count"),
            )
            .group_by(OrderItem.sku)
            .order_by(func.count(func.distinct(OrderItem.order_id)).desc(), OrderItem.sku)
            .all()
        )
        return [
            ProductRead(
                sku=row.sku,
                title=row.title,
                category=row.category,
                unit_paise=row.unit_paise,
                orders_count=row.orders_count,
            )
            for row in rows
        ]

    def list_policies(self) -> list[PolicyRead]:
        """Every policy rule with its human summary."""
        rows = self._session.query(Policy).order_by(Policy.rule_key).all()
        return [self._to_policy_dto(row) for row in rows]

    def get_product(self, sku: str) -> ProductDetailRead:
        """Product plus applicable refund/replacement policies, or 404."""
        products = {p.sku: p for p in self.list_products()}
        product = products.get(sku.upper())
        if product is None:
            raise NotFoundError(f"product {sku} not found")
        policies = {p.rule_key: p for p in self.list_policies()}
        ordered_keys = _REFUND_RULES + _REPLACEMENT_RULES + _GUARDRAIL_RULES
        applicable = [policies[key] for key in ordered_keys if key in policies]
        return ProductDetailRead(product=product, policies=applicable)

    @staticmethod
    def _to_policy_dto(row: Policy) -> PolicyRead:
        """Policy row to DTO with its human summary."""
        params = dict(row.params or {})
        return PolicyRead(
            rule_key=row.rule_key,
            summary=summarize_rule(row.rule_key, params),
            params=params,
            version=row.version,
        )
