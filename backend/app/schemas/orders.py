"""Phase 4 checkout/order DTOs: mock payment, orders, timeline (spec §§9-10)."""

from pydantic import BaseModel, Field


class CheckoutCreate(BaseModel):
    """Checkout form: cart → mock payment → order."""

    shipping_address: str = Field(min_length=10, max_length=500)


class PaymentRead(BaseModel):
    """Mock payment receipt."""

    payment_reference: str
    amount_paise: int
    amount_display: str
    status: str
    method: str
    paid_at: str


class OrderItemRead(BaseModel):
    """One order line (product snapshot)."""

    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price_paise: int
    line_total_paise: int


class TimelineStep(BaseModel):
    """One delivery-timeline step for the order UI."""

    key: str
    label: str
    done: bool
    at: str | None = None


class OrderListItem(BaseModel):
    """Order history row (`GET /orders`)."""

    id: str
    order_number: str
    status: str
    subtotal_paise: int
    total_paise: int
    total_display: str
    payment_status: str
    item_count: int
    ordered_at: str
    estimated_delivery: str


class OrderDetail(OrderListItem):
    """Order tracking page (`GET /orders/:id`)."""

    shipping_address: str
    delivered_at: str | None = None
    items: list[OrderItemRead]
    payment: PaymentRead
    timeline: list[TimelineStep]
