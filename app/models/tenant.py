"""Tenant ORM model.

A tenant represents a Nytia partner (IBM, Microsoft, etc.) whose workforce
health data we track. Every employee belongs to exactly one tenant.

Org-level recommendations are computed per tenant by aggregating the health
records of every employee that belongs to it.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.employee import Employee


class Tenant(Base):
    """A Nytia partner organisation."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employees: Mapped[list["Employee"]] = relationship(back_populates="tenant_ref")

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} name={self.name}>"
