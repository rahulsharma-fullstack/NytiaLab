"""Business logic for employee operations."""

from sqlalchemy.orm import Session

from app.models import Employee, HealthRecord
from app.repositories import EmployeeRepository


class EmployeeNotFoundError(Exception):
    """Raised when an employee ID doesn't exist in the database."""

    def __init__(self, employee_id: str) -> None:
        self.employee_id = employee_id
        super().__init__(f"Employee {employee_id!r} not found")


class EmployeeService:
    """Business logic for employee-related operations."""

    def __init__(self, db: Session) -> None:
        self.repo = EmployeeRepository(db)

    def get_employee(self, employee_id: str) -> Employee:
        """Fetch an employee by ID. Raises EmployeeNotFoundError if missing."""
        employee = self.repo.get_by_id(employee_id)
        if employee is None:
            raise EmployeeNotFoundError(employee_id)
        return employee

    def list_employees(self, limit: int = 100, offset: int = 0) -> list[Employee]:
        """List employees with pagination."""
        return self.repo.list_all(limit=limit, offset=offset)

    def get_health_records(self, employee_id: str) -> list[HealthRecord]:
        """Fetch health records for an employee. Validates employee exists first."""
        # Verify employee exists before fetching records
        self.get_employee(employee_id)
        return self.repo.get_health_records(employee_id)