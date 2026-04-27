"""Pydantic schemas for API request/response validation."""

from app.schemas.employee import EmployeeResponse
from app.schemas.health_record import HealthRecordResponse

__all__ = [
    "EmployeeResponse",
    "HealthRecordResponse",
]