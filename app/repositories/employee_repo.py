"""Repository for Employee database operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Employee, HealthRecord


class EmployeeRepository:
    """Data access layer for employees."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, employee_id: str) -> Employee | None:
        """Fetch a single employee by their ID. Returns None if not found."""
        stmt = select(Employee).where(Employee.id == employee_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_all(self, limit: int = 100, offset: int = 0) -> list[Employee]:
        """Return paginated list of employees."""
        stmt = select(Employee).order_by(Employee.id).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def get_health_records(self, employee_id: str) -> list[HealthRecord]:
        """Fetch all health records for a given employee, newest first."""
        stmt = (
            select(HealthRecord)
            .where(HealthRecord.employee_id == employee_id)
            .order_by(HealthRecord.record_date.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_all_by_tenant(self, tenant_id: str) -> list[Employee]:
        """Fetch every employee that belongs to a tenant.

        Eager-loads each employee's `health_records` via `selectinload` so the
        aggregator can read them without triggering N+1 queries.

        Used by the org-level aggregator (`app/services/org_aggregator.py`).
        Suitable for tenants with up to ~1000 employees; see the note in the
        aggregator for the path forward at larger scale.
        """
        stmt = (
            select(Employee)
            .where(Employee.tenant_id == tenant_id)
            .options(selectinload(Employee.health_records))
            .order_by(Employee.id)
        )
        return list(self.db.execute(stmt).scalars().all())
