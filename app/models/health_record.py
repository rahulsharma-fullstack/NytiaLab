"""Health record ORM model — one row per observation."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.employee import Employee


# Enum values as Python constants (used in CHECK constraints)
VALID_FACTORS = (
    "Sleep",
    "Depression",
    "Smoke",
    "Stress",
    "Movement",
    "Nutrition",
    "Wellness",
    "Obesity",
)
VALID_CONDITIONS = (
    "Type 2 Diabetes",
    "Cardiovascular Disease",
    "Chronic Kidney Disease",
    "Cancer",
    "Mental Illness",
    "Osteoporosis",
)
VALID_STATUSES = ("Suffering", "At Risk")
VALID_SEVERITIES = ("Important", "Very Important")
VALID_UNITS = ("score", "hours")


class HealthRecord(Base):
    """A single health observation for an employee.

    One row per (employee, date, factor, condition) tuple.
    """

    __tablename__ = "health_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    record_date: Mapped[date] = mapped_column(Date, nullable=False)

    factor: Mapped[str] = mapped_column(String(50), nullable=False)
    health_condition: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    improvement_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    employee: Mapped["Employee"] = relationship(back_populates="health_records")

    # Table-level constraints
    __table_args__ = (
        CheckConstraint(
            f"factor IN {VALID_FACTORS}",
            name="check_factor_valid",
        ),
        CheckConstraint(
            f"health_condition IN {VALID_CONDITIONS}",
            name="check_condition_valid",
        ),
        CheckConstraint(
            f"status IN {VALID_STATUSES}",
            name="check_status_valid",
        ),
        CheckConstraint(
            f"severity IN {VALID_SEVERITIES}",
            name="check_severity_valid",
        ),
        CheckConstraint(
            f"unit IN {VALID_UNITS}",
            name="check_unit_valid",
        ),
        Index("idx_health_records_employee", "employee_id"),
        Index("idx_health_records_condition", "health_condition"),
        Index("idx_health_records_factor", "factor"),
        Index("idx_health_records_date", "record_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<HealthRecord id={self.id} employee={self.employee_id} "
            f"factor={self.factor} condition={self.health_condition}>"
        )
