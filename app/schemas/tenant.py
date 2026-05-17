"""Pydantic schemas for the /tenants endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TenantResponse(BaseModel):
    """One tenant in the API response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime
