"""Recommendation log — audit trail of what we recommended to whom."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.product import Product


class Recommendation(Base):
    """Logged recommendation for audit and future ML feedback."""

    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False
    )
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    algorithm_version: Mapped[str] = mapped_column(String(20), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    employee: Mapped["Employee"] = relationship(back_populates="recommendations")
    product: Mapped["Product"] = relationship(back_populates="recommendations")

    __table_args__ = (
        Index("idx_recommendations_employee_time", "employee_id", "generated_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Recommendation id={self.id} employee={self.employee_id} "
            f"product={self.product_id} score={self.score}>"
        )