"""Employee ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.health_record import HealthRecord
    from app.models.recommendation import Recommendation


class Employee(Base):
    """An employee whose health data we track."""

    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    tenant: Mapped[str] = mapped_column(String(50), nullable=False, default="NYTIA")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    health_records: Mapped[list["HealthRecord"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Employee id={self.id} region={self.region}>"
