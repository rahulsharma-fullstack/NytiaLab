"""Pydantic schemas for Product endpoints."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProductConditionResponse(BaseModel):
    """A condition this product helps address."""

    model_config = ConfigDict(from_attributes=True)

    health_condition: str
    relevance_score: Decimal


class ProductFactorResponse(BaseModel):
    """A contributing factor this product targets."""

    model_config = ConfigDict(from_attributes=True)

    factor: str
    relevance_score: Decimal


class ProductResponse(BaseModel):
    """A product (wellness service) summary, without related tags."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    category: str
    service_type: str
    price: Decimal | None
    currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductDetailResponse(ProductResponse):
    """A product with its full condition and factor tags."""

    conditions: list[ProductConditionResponse]
    factors: list[ProductFactorResponse]
