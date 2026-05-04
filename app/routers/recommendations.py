"""HTTP endpoints for recommendations."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import RecommendationItem, RecommendationResponse
from app.services import EmployeeNotFoundError, RecommenderService

router = APIRouter(prefix="/recommend", tags=["recommendations"])


@router.get(
    "/{employee_id}",
    response_model=RecommendationResponse,
    summary="Get personalized wellness service recommendations",
)
def get_recommendations(
    employee_id: str,
    top_n: int = Query(default=10, ge=1, le=50, description="Number of recommendations"),
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    """Generate ranked, explained wellness service recommendations for an employee."""
    service = RecommenderService(db)
    try:
        bundle = service.recommend(employee_id, top_n=top_n)
    except EmployeeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    items = [
        RecommendationItem(
            product_id=sp.product.id,
            name=sp.product.name,
            category=sp.product.category,
            service_type=sp.product.service_type,
            price=sp.product.price,
            score=round(sp.score, 4),
            reasons=sp.reasons,
        )
        for sp in bundle.items
    ]

    return RecommendationResponse(
        employee_id=bundle.employee_id,
        generated_at=bundle.generated_at,
        algorithm_version=bundle.algorithm_version,
        recommendations=items,
    )
