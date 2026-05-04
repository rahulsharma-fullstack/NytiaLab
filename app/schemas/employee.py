"""Pydantic schemas for Employee endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EmployeeResponse(BaseModel):
    """Employee data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    region: str
    tenant: str
    created_at: datetime
    updated_at: datetime
