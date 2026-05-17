"""Pydantic schemas for the org-level (tenant) endpoints.

These are the JSON shapes the HTTP layer returns. They are deliberately
flat and dashboard-friendly; the math lives in `app/services/scoring.py`
and `app/services/org_aggregator.py`.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DimensionPressureResponse(BaseModel):
    """One condition or one factor in a workforce profile."""

    name: str
    suffering_count: int
    at_risk_count: int
    total_affected: int
    percent_affected: float
    pressure_score: float


class TenantProfileResponse(BaseModel):
    """Workforce health summary returned by /tenants/{id}/profile."""

    tenant_id: str
    tenant_name: str
    total_employees: int
    conditions: list[DimensionPressureResponse] = Field(default_factory=list)
    factors: list[DimensionPressureResponse] = Field(default_factory=list)


class OrgRecommendationItem(BaseModel):
    """A single ranked product recommendation for a tenant."""

    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    category: str
    service_type: str
    price: Decimal | None
    currency: str
    score: float
    reasons: list[str]


class OrgRecommendationResponse(BaseModel):
    """Full response for /tenants/{id}/recommendations."""

    tenant_id: str
    tenant_name: str
    total_employees: int
    algorithm_version: str
    generated_at: datetime
    recommendations: list[OrgRecommendationItem] = Field(default_factory=list)
