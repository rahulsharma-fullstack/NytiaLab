"""HTTP endpoints for employee operations.

Service exceptions (EmployeeNotFoundError, ...) are handled centrally in
`app.exceptions`, so routers stay tight and just call the service layer.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import EmployeeResponse, HealthRecordResponse
from app.services import EmployeeService

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get(
    "",
    response_model=list[EmployeeResponse],
    summary="List employees",
)
def list_employees(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[EmployeeResponse]:
    """Return a paginated list of employees."""
    service = EmployeeService(db)
    employees = service.list_employees(limit=limit, offset=offset)
    return [EmployeeResponse.model_validate(emp) for emp in employees]


@router.get(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Get employee by ID",
)
def get_employee(
    employee_id: str,
    db: Session = Depends(get_db),
) -> EmployeeResponse:
    """Return a single employee by their ID."""
    service = EmployeeService(db)
    employee = service.get_employee(employee_id)
    return EmployeeResponse.model_validate(employee)


@router.get(
    "/{employee_id}/health-records",
    response_model=list[HealthRecordResponse],
    summary="Get all health records for an employee",
)
def get_employee_health_records(
    employee_id: str,
    db: Session = Depends(get_db),
) -> list[HealthRecordResponse]:
    """Return all health records for the given employee, newest first."""
    service = EmployeeService(db)
    records = service.get_health_records(employee_id)
    return [HealthRecordResponse.model_validate(rec) for rec in records]
