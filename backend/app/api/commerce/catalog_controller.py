"""Catalog controller: read-only products + policies for the console."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.commerce.catalog import PolicyRead, ProductDetailRead, ProductRead
from app.services.commerce.catalog_service import CatalogService

router = APIRouter(tags=["catalog"])


@router.get("/api/catalog/products", response_model=list[ProductRead])
def list_products(session: Session = Depends(get_db)) -> list[ProductRead]:
    """Dummy product catalog (distinct SKUs across orders)."""
    return CatalogService(session).list_products()


@router.get("/api/catalog/products/{sku}", response_model=ProductDetailRead)
def get_product(sku: str, session: Session = Depends(get_db)) -> ProductDetailRead:
    """One product with the policies that apply to it."""
    return CatalogService(session).get_product(sku)


@router.get("/api/catalog/policies", response_model=list[PolicyRead])
def list_policies(session: Session = Depends(get_db)) -> list[PolicyRead]:
    """Every policy rule with a human-readable summary."""
    return CatalogService(session).list_policies()
