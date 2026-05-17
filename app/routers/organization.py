"""HTTP endpoints for the org-level (tenant) recommendation flow.

Routes:
    GET /tenants                              List tenants
    GET /tenants/{tenant_id}                  Single tenant
    GET /tenants/{tenant_id}/profile          Workforce health summary
    GET /tenants/{tenant_id}/recommendations  Top N org-level recommendations

TenantNotFoundError is translated to a 404 by the centralised handler in
`app.exceptions`. Validation errors from `top_n` bounds are translated by
the same centralised handler.

# TODO: Production tenant isolation requires authentication.
# Currently tenant_id comes from the URL with no auth check.
# Production: JWT auth with tenant claim, every query scoped to the
# authenticated tenant's tenant_id, never trust the URL parameter alone.
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.rate_limit import RECOMMEND_LIMIT, limiter
from app.schemas import (
    DimensionPressureResponse,
    OrgRecommendationItem,
    OrgRecommendationResponse,
    TenantProfileResponse,
    TenantResponse,
)
from app.services import OrgRecommenderService, TenantService

router = APIRouter(prefix="/tenants", tags=["tenants"])


# ---------- tenant listing ----------


@router.get(
    "",
    response_model=list[TenantResponse],
    summary="List all tenants",
)
def list_tenants(db: Session = Depends(get_db)) -> list[TenantResponse]:
    """Return every tenant. Used by the org-demo dropdown."""
    tenants = TenantService(db).list_tenants()
    return [TenantResponse.model_validate(t) for t in tenants]


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Get one tenant by ID",
)
def get_tenant(tenant_id: str, db: Session = Depends(get_db)) -> TenantResponse:
    """Return one tenant. 404 if the ID is unknown."""
    tenant = TenantService(db).get_tenant(tenant_id)
    return TenantResponse.model_validate(tenant)


# ---------- workforce profile ----------


@router.get(
    "/{tenant_id}/profile",
    response_model=TenantProfileResponse,
    summary="Aggregated workforce health summary for a tenant",
)
def get_tenant_profile(tenant_id: str, db: Session = Depends(get_db)) -> TenantProfileResponse:
    """Return the per-condition and per-factor pressure rollup for a tenant.

    Raises `TenantNotFoundError` (-> 404) if the tenant does not exist.
    Returns empty conditions/factors lists if the tenant has no records.
    """
    tenant_service = TenantService(db)
    tenant = tenant_service.get_tenant(tenant_id)

    # The bundle from OrgRecommenderService already carries the workforce
    # profile, but the profile endpoint only needs the aggregation, not
    # the scoring. Use the aggregator directly to keep the call cheap.
    from app.services.org_aggregator import aggregate_workforce  # local import to avoid cycle

    workforce = aggregate_workforce(tenant_id, db)

    return TenantProfileResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        total_employees=workforce.total_employees,
        conditions=[
            DimensionPressureResponse(
                name=dp.name,
                suffering_count=dp.suffering_count,
                at_risk_count=dp.at_risk_count,
                total_affected=dp.total_affected,
                percent_affected=dp.percent_affected(workforce.total_employees),
                pressure_score=dp.pressure_score,
            )
            for dp in workforce.conditions
        ],
        factors=[
            DimensionPressureResponse(
                name=dp.name,
                suffering_count=dp.suffering_count,
                at_risk_count=dp.at_risk_count,
                total_affected=dp.total_affected,
                percent_affected=dp.percent_affected(workforce.total_employees),
                pressure_score=dp.pressure_score,
            )
            for dp in workforce.factors
        ],
    )


# ---------- recommendations ----------


@router.get(
    "/{tenant_id}/recommendations",
    response_model=OrgRecommendationResponse,
    summary="Ranked bulk wellness recommendations for a tenant",
)
@limiter.limit(RECOMMEND_LIMIT)
def get_tenant_recommendations(
    request: Request,
    tenant_id: str,
    top_n: int = Query(default=10, ge=1, le=50, description="Number of recommendations"),
    db: Session = Depends(get_db),
) -> OrgRecommendationResponse:
    """Aggregate the workforce, then return the top N ranked products.

    Raises `TenantNotFoundError` (-> 404) if the tenant does not exist.
    Same 30/min rate limit as the per-employee /recommend endpoint.
    """
    # Validate tenant exists and get the human-readable name for the response.
    tenant = TenantService(db).get_tenant(tenant_id)

    bundle = OrgRecommenderService(db).recommend(tenant_id, top_n=top_n)

    items = [
        OrgRecommendationItem(
            product_id=sp.product.id,
            product_name=sp.product.name,
            category=sp.product.category,
            service_type=sp.product.service_type,
            price=sp.product.price,
            currency=sp.product.currency,
            score=sp.score,
            reasons=sp.reasons,
        )
        for sp in bundle.items
    ]

    return OrgRecommendationResponse(
        tenant_id=bundle.tenant_id,
        tenant_name=tenant.name,
        total_employees=bundle.total_employees,
        algorithm_version=bundle.algorithm_version,
        generated_at=bundle.generated_at,
        recommendations=items,
    )
