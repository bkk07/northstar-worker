"""Products + cart controller (Phase 3).

Public: `GET /products`, `GET /products/:id`, `GET /products-meta/categories`.
Authenticated (CUSTOMER or staff preview): cart endpoints.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.deps import get_db
from app.schemas.products import (
    CartItemCreate,
    CartItemUpdate,
    CartRead,
    ProductDetail,
    ProductListItem,
)
from app.services.products import cart_service, product_service

router = APIRouter(tags=["products"])


@router.get("/products", response_model=list[ProductListItem])
def list_products(
    q: str | None = None,
    category: str | None = None,
    sort: str = "name",
    session: Session = Depends(get_db),
) -> list[dict]:
    """Browse the catalog (search, category filter, sort)."""
    return product_service.list_products(session, q=q, category=category, sort=sort)


@router.get("/products-meta/categories", response_model=list[str])
def list_categories(session: Session = Depends(get_db)) -> list[str]:
    """Distinct categories for the filter UI."""
    return product_service.list_categories(session)


@router.get("/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: str, session: Session = Depends(get_db)) -> dict:
    """Product detail with policy summary."""
    return product_service.get_product(session, product_id=product_id)


@router.get("/cart", response_model=CartRead)
def get_cart(
    claims: dict = Depends(get_current_user), session: Session = Depends(get_db)
) -> dict:
    """Active cart for the bearer subject."""
    return cart_service.get_cart(session, user_id=str(claims["sub"]))


@router.post("/cart/items", response_model=CartRead, status_code=status.HTTP_201_CREATED)
def add_cart_item(
    payload: CartItemCreate,
    claims: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict:
    """Add a product to the cart (price snapshotted)."""
    return cart_service.add_item(
        session,
        user_id=str(claims["sub"]),
        product_id=payload.product_id,
        quantity=payload.quantity,
    )


@router.patch("/cart/items/{item_id}", response_model=CartRead)
def update_cart_item(
    item_id: str,
    payload: CartItemUpdate,
    claims: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict:
    """Change a cart line quantity."""
    return cart_service.update_item(
        session, user_id=str(claims["sub"]), item_id=item_id, quantity=payload.quantity
    )


@router.delete("/cart/items/{item_id}", response_model=CartRead)
def remove_cart_item(
    item_id: str,
    claims: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict:
    """Remove a cart line."""
    return cart_service.remove_item(session, user_id=str(claims["sub"]), item_id=item_id)
