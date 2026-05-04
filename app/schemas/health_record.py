"""Pydantic schemas for HealthRecord endpoints."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class HealthRecordResponse(BaseModel):
    """A single health record returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: str
    record_date: date
    factor: str
    health_condition: str
    status: str
    severity: str
    value: Decimal
    unit: str
    improvement_rate: Decimal | None
    created_at: datetime
