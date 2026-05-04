"""Repository for Product database operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Product, ProductCondition, ProductFactor


class ProductRepository:
    """Data access layer for products and their tags."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, product_id: int) -> Product | None:
        """Fetch a product with its condition and factor tags."""
        stmt = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                selectinload(Product.conditions),
                selectinload(Product.factors),
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_products(
        self,
        category: str | None = None,
        service_type: str | None = None,
        condition: str | None = None,
        factor: str | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Product]:
        """List products, optionally filtered by various criteria.

        Filters are AND-combined. None means "don't filter on this dimension."
        """
        stmt = select(Product)

        if active_only:
            stmt = stmt.where(Product.is_active.is_(True))
        if category is not None:
            stmt = stmt.where(Product.category == category)
        if service_type is not None:
            stmt = stmt.where(Product.service_type == service_type)
        if condition is not None:
            stmt = stmt.join(ProductCondition).where(ProductCondition.health_condition == condition)
        if factor is not None:
            stmt = stmt.join(ProductFactor).where(ProductFactor.factor == factor)

        stmt = stmt.order_by(Product.id).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())
