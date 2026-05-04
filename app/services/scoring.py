"""Recommendation scoring logic.

Pure functions, no DB access, no side effects. Easy to test.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from app.models import HealthRecord, Product

# Weights for the scoring formula.
# Tuning these is how you change recommendation behavior.
SEVERITY_WEIGHT = {
    "Very Important": 1.5,
    "Important": 1.0,
}

STATUS_WEIGHT = {
    "Suffering": 1.2,
    "At Risk": 1.0,
}

CONDITION_MATCH_BASE = 2.0  # Direct condition match worth more than factor match
FACTOR_MATCH_BASE = 1.5

ALGORITHM_VERSION = "rules-v1"


@dataclass
class ScoredProduct:
    """A product with its computed score and the reasons it was selected."""

    product: Product
    score: float
    reasons: list[str]


def score_product_for_employee(
    product: Product,
    health_records: Iterable[HealthRecord],
) -> ScoredProduct:
    """Score a single product against an employee's health records.

    Returns a ScoredProduct with:
    - score: a float (higher = better match)
    - reasons: human-readable explanations for why this was recommended
    """
    score = 0.0
    reasons: list[str] = []

    # Build sets of (condition, severity, status) and (factor, severity, status)
    # tuples from the employee's health records.
    employee_conditions = {
        (rec.health_condition, rec.severity, rec.status) for rec in health_records
    }
    employee_factors = {
        (rec.factor, rec.severity, rec.status) for rec in health_records
    }

    # Build lookup tables of what this product targets.
    product_conditions = {pc.health_condition: float(pc.relevance_score) for pc in product.conditions}
    product_factors = {pf.factor: float(pf.relevance_score) for pf in product.factors}

    # Score condition matches (direct disease targeting)
    for condition, severity, status in employee_conditions:
        if condition in product_conditions:
            relevance = product_conditions[condition]
            sev_w = SEVERITY_WEIGHT.get(severity, 1.0)
            stat_w = STATUS_WEIGHT.get(status, 1.0)
            contribution = CONDITION_MATCH_BASE * relevance * sev_w * stat_w
            score += contribution
            reasons.append(
                f"Targets your {condition} ({status}, {severity})"
            )

    # Score factor matches (preventive lifestyle targeting)
    for factor, severity, status in employee_factors:
        if factor in product_factors:
            relevance = product_factors[factor]
            sev_w = SEVERITY_WEIGHT.get(severity, 1.0)
            stat_w = STATUS_WEIGHT.get(status, 1.0)
            contribution = FACTOR_MATCH_BASE * relevance * sev_w * stat_w
            score += contribution
            reasons.append(
                f"Addresses your {factor} factor ({status}, {severity})"
            )

    return ScoredProduct(product=product, score=score, reasons=reasons)


def rank_products(
    products: Iterable[Product],
    health_records: Iterable[HealthRecord],
    top_n: int = 10,
) -> list[ScoredProduct]:
    """Score and rank products. Returns top N scored products with score > 0.

    Products that don't match anything are excluded.
    """
    health_records_list = list(health_records)

    scored = [
        score_product_for_employee(product, health_records_list)
        for product in products
    ]

    # Filter out zero-score products (they don't match the employee at all)
    scored = [sp for sp in scored if sp.score > 0]

    # Sort by score, highest first
    scored.sort(key=lambda sp: sp.score, reverse=True)

    return scored[:top_n]