"""Product (wellness service) ORM model."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.product_tag import ProductCondition, ProductFactor
    from app.models.recommendation import Recommendation


VALID_SERVICE_TYPES = ("factor_service", "condition_service")


class Product(Base):
    """A wellness service that can be recommended to employees."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    service_type: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    conditions: Mapped[list["ProductCondition"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    factors: Mapped[list["ProductFactor"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="product"
    )

    __table_args__ = (
        CheckConstraint(
            f"service_type IN {VALID_SERVICE_TYPES}",
            name="check_service_type_valid",
        ),
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} name={self.name!r} type={self.service_type}>"