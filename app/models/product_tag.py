"""Product tagging tables — link products to conditions and factors."""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.health_record import VALID_CONDITIONS, VALID_FACTORS

if TYPE_CHECKING:
    from app.models.product import Product


class ProductCondition(Base):
    """Links a product to a health condition it addresses."""

    __tablename__ = "product_conditions"

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    health_condition: Mapped[str] = mapped_column(String(100), primary_key=True)
    relevance_score: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("1.00"), nullable=False
    )

    product: Mapped["Product"] = relationship(back_populates="conditions")

    __table_args__ = (
        CheckConstraint(
            f"health_condition IN {VALID_CONDITIONS}",
            name="check_product_condition_valid",
        ),
        Index("idx_product_conditions_condition", "health_condition"),
    )


class ProductFactor(Base):
    """Links a product to a contributing factor it targets."""

    __tablename__ = "product_factors"

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    factor: Mapped[str] = mapped_column(String(50), primary_key=True)
    relevance_score: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("1.00"), nullable=False
    )

    product: Mapped["Product"] = relationship(back_populates="factors")

    __table_args__ = (
        CheckConstraint(
            f"factor IN {VALID_FACTORS}",
            name="check_product_factor_valid",
        ),
        Index("idx_product_factors_factor", "factor"),
    )