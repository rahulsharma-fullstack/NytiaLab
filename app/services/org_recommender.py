"""Org-level recommender orchestration.

Given a tenant id, this service:

1. Aggregates the tenant's workforce health profile (via `org_aggregator`).
2. Pulls the active product catalogue (via `ProductRepository`).
3. Scores every product against the workforce and returns the top N
   (via `scoring.rank_products_for_organization`).

It returns a small bundle dataclass. `tenant_name` is intentionally NOT in
this bundle: the service speaks in tenant ids, the router shapes the JSON
response (and is the place that knows how to look up the human-readable
tenant name via TenantService in Phase 4).

Audit logging is intentionally skipped for now; we can add an org-level
audit table later if the sponsor asks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.repositories import ProductRepository
from app.services.org_aggregator import WorkforceProfile, aggregate_workforce
from app.services.scoring import (
    ORG_ALGORITHM_VERSION,
    OrgScoredProduct,
    rank_products_for_organization,
)


@dataclass
class OrgRecommendationBundle:
    """Output of `OrgRecommenderService.recommend`."""

    tenant_id: str
    total_employees: int
    generated_at: datetime
    algorithm_version: str
    items: list[OrgScoredProduct] = field(default_factory=list)
    workforce: WorkforceProfile | None = None  # included so the router can
    # populate the profile endpoint without re-running aggregation


class OrgRecommenderService:
    """Generates ranked wellness recommendations for a whole tenant."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.product_repo = ProductRepository(db)

    def recommend(self, tenant_id: str, top_n: int = 10) -> OrgRecommendationBundle:
        """Build the workforce profile, then score and rank the catalogue.

        An unknown tenant id is handled here by returning an empty bundle
        rather than raising. The router (Phase 4) is responsible for the
        404 case via `TenantService.get_tenant(tenant_id)` before calling
        this method. That keeps this layer focused on the math.
        """
        workforce = aggregate_workforce(tenant_id, self.db)

        if workforce.total_employees == 0:
            return OrgRecommendationBundle(
                tenant_id=tenant_id,
                total_employees=0,
                generated_at=datetime.now(UTC),
                algorithm_version=ORG_ALGORITHM_VERSION,
                items=[],
                workforce=workforce,
            )

        # Fetch the active product catalogue. Same approach as the
        # per-employee recommender: small catalogue (~12 today), full
        # scoring is fine. For a larger catalogue we could pre-filter.
        candidates = self.product_repo.list_products(active_only=True, limit=500, offset=0)
        # Eager-load tags so the scoring function can read them without
        # triggering N+1 queries.
        candidate_ids = [p.id for p in candidates]
        candidates_full = [self.product_repo.get_by_id(pid) for pid in candidate_ids]
        candidates_full = [c for c in candidates_full if c is not None]

        scored = rank_products_for_organization(candidates_full, workforce, top_n=top_n)

        return OrgRecommendationBundle(
            tenant_id=tenant_id,
            total_employees=workforce.total_employees,
            generated_at=datetime.now(UTC),
            algorithm_version=ORG_ALGORITHM_VERSION,
            items=scored,
            workforce=workforce,
        )
