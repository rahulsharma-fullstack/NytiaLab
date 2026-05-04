"""Business logic for product operations."""

from sqlalchemy.orm import Session

from app.models import Product
from app.repositories import ProductRepository


class ProductNotFoundError(Exception):
    """Raised when a product ID doesn't exist in the database."""

    def __init__(self, product_id: int) -> None:
        self.product_id = product_id
        super().__init__(f"Product {product_id} not found")


class ProductService:
    """Business logic for product-related operations."""

    def __init__(self, db: Session) -> None:
        self.repo = ProductRepository(db)

    def get_product(self, product_id: int) -> Product:
        """Fetch a product with full tags. Raises ProductNotFoundError if missing."""
        product = self.repo.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        return product

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
        """List products with optional filters."""
        return self.repo.list_products(
            category=category,
            service_type=service_type,
            condition=condition,
            factor=factor,
            active_only=active_only,
            limit=limit,
            offset=offset,
        )
