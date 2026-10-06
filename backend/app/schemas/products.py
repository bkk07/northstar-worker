"""Phase 3 storefront DTOs: products, policies, cart (spec §16)."""

from pydantic import BaseModel, Field


class PolicySummary(BaseModel):
    """Per-product policy flags plus a one-line human summary."""

    return_allowed: bool
    return_window_days: int
    refund_allowed: bool
    replacement_allowed: bool
    replacement_window_days: int
    cancellation_allowed: bool
    warranty_days: int
    summary: str


class ProductListItem(BaseModel):
    """Product card row (`GET /products`)."""

    id: str
    name: str
    slug: str
    category: str
    brand: str
    price_paise: int
    price_display: str
    image_url: str
    stock: int
    in_stock: bool


class ProductDetail(BaseModel):
    """Product page (`GET /products/:id`) with policy summary."""

    id: str
    name: str
    slug: str
    description: str
    category: str
    brand: str
    price_paise: int
    price_display: str
    image_url: str
    stock: int
    in_stock: bool
    policy: PolicySummary


class CartItemRead(BaseModel):
    """One cart line."""

    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price_paise: int
    line_total_paise: int


class CartRead(BaseModel):
    """Active cart with totals."""

    id: str
    items: list[CartItemRead]
    subtotal_paise: int
    total_paise: int
    item_count: int


class CartItemCreate(BaseModel):
    """Add a product to the cart."""

    product_id: str = Field(min_length=1)
    quantity: int = Field(default=1, ge=1, le=99)


class CartItemUpdate(BaseModel):
    """Change a cart line quantity."""

    quantity: int = Field(ge=1, le=99)
