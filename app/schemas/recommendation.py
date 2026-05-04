"""Pydantic schemas for recommendation endpoints."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class RecommendationItem(BaseModel):
    """A single recommended product with its score and reasons."""

    model_config = ConfigDict(from_attributes=True)

    product_id: int
    name: str
    category: str
    service_type: str
    price: Decimal | None
    score: float
    reasons: list[str]


class RecommendationResponse(BaseModel):
    """The full recommendation response for an employee."""

    employee_id: str
    generated_at: datetime
    algorithm_version: str
    recommendations: list[RecommendationItem]