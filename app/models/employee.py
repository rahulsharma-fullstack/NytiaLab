"""Employee ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.health_record import HealthRecord
    from app.models.recommendation import Recommendation
    from app.models.tenant import Tenant


class Employee(Base):
    """An employee whose health data we track."""

    __tablename__ = "employees"

    # Widened from String(10) to String(20) so the new tenant-prefixed IDs
    # (e.g. "E_MICROSOFT_001") fit. The legacy E0001-style IDs still fit.
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    region: Mapped[str] = mapped_column(String(100), nullable=False)

    # Legacy free-text tenant column. Kept alongside `tenant_id` so existing
    # callers and data are not disturbed. New code should prefer `tenant_id`
    # and the `tenant_ref` relationship below.
    tenant: Mapped[str] = mapped_column(String(50), nullable=False, default="NYTIA")

    # Foreign key to the proper tenants table. Backfilled to T_NYTIA_DEMO
    # for the original 8 employees during the add-tenants migration.
    tenant_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("tenants.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    tenant_ref: Mapped["Tenant"] = relationship(back_populates="employees")
    health_records: Mapped[list["HealthRecord"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_employees_tenant_id", "tenant_id"),)

    def __repr__(self) -> str:
        return f"<Employee id={self.id} region={self.region} tenant_id={self.tenant_id}>"
