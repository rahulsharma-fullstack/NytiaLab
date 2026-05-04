"""Recommendation orchestration service.

Pulls together employee data, candidate products, and scoring
to produce ranked, explained recommendations.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Recommendation
from app.repositories import ProductRepository
from app.services.employee_service import EmployeeService
from app.services.scoring import ALGORITHM_VERSION, ScoredProduct, rank_products


@dataclass
class RecommendationBundle:
    """The full result of a recommendation request."""

    employee_id: str
    generated_at: datetime
    algorithm_version: str
    items: list[ScoredProduct]


class RecommenderService:
    """Generates wellness service recommendations for an employee."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.employee_service = EmployeeService(db)
        self.product_repo = ProductRepository(db)

    def recommend(self, employee_id: str, top_n: int = 10) -> RecommendationBundle:
        """Generate top-N recommendations for an employee.

        Raises EmployeeNotFoundError if the employee doesn't exist.
        Logs each recommendation to the audit table.
        """
        # 1. Verify employee exists and get their health records
        self.employee_service.get_employee(employee_id)
        records = self.employee_service.get_health_records(employee_id)

        # 2. If the employee has no health records, return empty results
        if not records:
            return RecommendationBundle(
                employee_id=employee_id,
                generated_at=datetime.now(UTC),
                algorithm_version=ALGORITHM_VERSION,
                items=[],
            )

        # 3. Pull candidate products. For now, we score against the entire active catalog.
        #    Later we could pre-filter to only products tagged for the employee's
        #    conditions/factors, but for a small catalog (~12 products) full scoring is fine.
        candidates = self.product_repo.list_products(
            active_only=True,
            limit=500,
            offset=0,
        )

        # 4. Eager-load conditions/factors for each candidate so the scoring function
        #    can read them without triggering N+1 queries.
        candidate_ids = [p.id for p in candidates]
        candidates_full = [self.product_repo.get_by_id(pid) for pid in candidate_ids]
        # Filter out any None values (shouldn't happen but defensive)
        candidates_full = [c for c in candidates_full if c is not None]

        # 5. Score and rank
        scored = rank_products(candidates_full, records, top_n=top_n)

        # 6. Diversify: ensure mix of factor and condition services in top results.
        scored = self._diversify(scored, top_n=top_n)

        # 7. Log recommendations for audit
        self._log_recommendations(employee_id, scored)

        return RecommendationBundle(
            employee_id=employee_id,
            generated_at=datetime.now(UTC),
            algorithm_version=ALGORITHM_VERSION,
            items=scored,
        )

    def _diversify(
        self,
        scored: list[ScoredProduct],
        top_n: int,
    ) -> list[ScoredProduct]:
        """Ensure top results contain a mix of factor and condition services.

        If top_n results are all the same service_type, swap in the
        highest-scoring product of the other type to add diversity.
        """
        if len(scored) <= 1:
            return scored

        top = scored[:top_n]
        types_in_top = {sp.product.service_type for sp in top}

        # If we already have both types, no diversification needed
        if len(types_in_top) > 1:
            return top

        # We have only one type in top_n. Find the best product of the other type.
        only_type = next(iter(types_in_top))
        other_type = "condition_service" if only_type == "factor_service" else "factor_service"

        for sp in scored:
            if sp.product.service_type == other_type:
                # Replace the lowest-scoring item in top with this one
                top[-1] = sp
                # Re-sort to maintain score order
                top.sort(key=lambda x: x.score, reverse=True)
                break

        return top

    def _log_recommendations(
        self,
        employee_id: str,
        scored: list[ScoredProduct],
    ) -> None:
        """Insert audit records for the generated recommendations."""
        if not scored:
            return

        rows = [
            Recommendation(
                employee_id=employee_id,
                product_id=sp.product.id,
                score=Decimal(str(round(sp.score, 4))),
                reason="; ".join(sp.reasons) if sp.reasons else None,
                algorithm_version=ALGORITHM_VERSION,
            )
            for sp in scored
        ]
        self.db.add_all(rows)
        self.db.commit()
