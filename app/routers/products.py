"""HTTP endpoints for product (wellness service) operations."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ProductDetailResponse, ProductResponse
from app.services import ProductNotFoundError, ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get(
    "",
    response_model=list[ProductResponse],
    summary="List products with optional filters",
)
def list_products(
    category: str | None = Query(default=None, description="Filter by category"),
    service_type: str | None = Query(
        default=None,
        description="Filter by service type: factor_service or condition_service",
    ),
    condition: str | None = Query(
        default=None,
        description="Filter by health condition the product addresses",
    ),
    factor: str | None = Query(
        default=None,
        description="Filter by contributing factor the product targets",
    ),
    active_only: bool = Query(default=True, description="Only return active products"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[ProductResponse]:
    """Return a paginated list of products. Supports several filter dimensions."""
    service = ProductService(db)
    products = service.list_products(
        category=category,
        service_type=service_type,
        condition=condition,
        factor=factor,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )
    return [ProductResponse.model_validate(p) for p in products]


@router.get(
    "/{product_id}",
    response_model=ProductDetailResponse,
    summary="Get product details with all tags",
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
) -> ProductDetailResponse:
    """Return full product details including condition and factor tags."""
    service = ProductService(db)
    try:
        product = service.get_product(product_id)
    except ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return ProductDetailResponse.model_validate(product)
