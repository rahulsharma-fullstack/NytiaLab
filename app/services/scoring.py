"""Recommendation scoring logic.

Pure functions, no DB access, no side effects. Easy to test.

Two scoring tracks live in this module:

- `score_product_for_employee` + `rank_products`: per-employee scoring.
  Used by the existing `/recommend/{employee_id}` flow.
- `score_product_for_organization` + `rank_products_for_organization`:
  workforce-wide scoring. Reuses the same base weights so the math is
  a population-summed version of the per-employee score.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.models import HealthRecord, Product

if TYPE_CHECKING:
    from app.services.org_aggregator import WorkforceProfile

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
ML_ALGORITHM_VERSION = "rules-ml-v1"
ORG_ALGORITHM_VERSION = "org-rules-v1"

# When the ML predictor flags a high risk on a condition the employee does not
# yet have, products targeting that condition get a bonus. The bonus is
# capped so it never out-weighs a direct condition match.
ML_RISK_BOOST_BASE = 1.5  # multiplied by risk probability (0..1)
ML_RISK_PROB_THRESHOLD = 0.6  # probabilities below this are ignored


@dataclass
class ScoredProduct:
    """A product with its computed score and the reasons it was selected."""

    product: Product
    score: float
    reasons: list[str]


def score_product_for_employee(
    product: Product,
    health_records: Iterable[HealthRecord],
    risk_scores: dict[str, float] | None = None,
) -> ScoredProduct:
    """Score a single product against an employee's health records.

    Returns a ScoredProduct with:
    - score: a float (higher = better match)
    - reasons: human-readable explanations for why this was recommended

    If `risk_scores` is provided, products targeting conditions the employee
    has *not* yet been diagnosed with but for which the ML model predicts
    elevated risk receive an additional bonus.
    """
    score = 0.0
    reasons: list[str] = []

    # Build sets of (condition, severity, status) and (factor, severity, status)
    # tuples from the employee's health records.
    employee_conditions = {
        (rec.health_condition, rec.severity, rec.status) for rec in health_records
    }
    employee_factors = {(rec.factor, rec.severity, rec.status) for rec in health_records}
    employee_condition_names = {c for c, _, _ in employee_conditions}

    # Build lookup tables of what this product targets.
    product_conditions = {
        pc.health_condition: float(pc.relevance_score) for pc in product.conditions
    }
    product_factors = {pf.factor: float(pf.relevance_score) for pf in product.factors}

    # Score condition matches (direct disease targeting)
    for condition, severity, status in employee_conditions:
        if condition in product_conditions:
            relevance = product_conditions[condition]
            sev_w = SEVERITY_WEIGHT.get(severity, 1.0)
            stat_w = STATUS_WEIGHT.get(status, 1.0)
            contribution = CONDITION_MATCH_BASE * relevance * sev_w * stat_w
            score += contribution
            reasons.append(f"Targets your {condition} ({status}, {severity})")

    # Score factor matches (preventive lifestyle targeting)
    for factor, severity, status in employee_factors:
        if factor in product_factors:
            relevance = product_factors[factor]
            sev_w = SEVERITY_WEIGHT.get(severity, 1.0)
            stat_w = STATUS_WEIGHT.get(status, 1.0)
            contribution = FACTOR_MATCH_BASE * relevance * sev_w * stat_w
            score += contribution
            reasons.append(f"Addresses your {factor} factor ({status}, {severity})")

    # ML risk boost: if the model predicts elevated risk on a condition that is
    # not already in the employee's records, give a small boost to products
    # targeting that condition.
    if risk_scores:
        for condition, probability in risk_scores.items():
            if probability < ML_RISK_PROB_THRESHOLD:
                continue
            if condition in employee_condition_names:
                continue  # already a direct condition match, handled above
            if condition in product_conditions:
                relevance = product_conditions[condition]
                contribution = ML_RISK_BOOST_BASE * relevance * probability
                score += contribution
                reasons.append(
                    f"ML predicts elevated {condition} risk ({int(round(probability * 100))}%)"
                )

    return ScoredProduct(product=product, score=score, reasons=reasons)


def rank_products(
    products: Iterable[Product],
    health_records: Iterable[HealthRecord],
    top_n: int = 10,
    risk_scores: dict[str, float] | None = None,
) -> list[ScoredProduct]:
    """Score and rank products. Returns top N scored products with score > 0.

    Products that don't match anything are excluded.
    """
    health_records_list = list(health_records)

    scored = [
        score_product_for_employee(product, health_records_list, risk_scores=risk_scores)
        for product in products
    ]

    # Filter out zero-score products (they don't match the employee at all)
    scored = [sp for sp in scored if sp.score > 0]

    # Sort by score, highest first
    scored.sort(key=lambda sp: sp.score, reverse=True)

    return scored[:top_n]


# =====================================================================
# Org-level scoring (algorithm version: org-rules-v1)
# =====================================================================
#
# Org score for one product = sum across matching conditions of
#   CONDITION_MATCH_BASE * relevance * condition_pressure_score
# plus sum across matching factors of
#   FACTOR_MATCH_BASE * relevance * factor_pressure_score
#
# Where pressure_score itself is sum of (severity_weight * status_weight)
# across every record in the tenant. So mathematically:
#
#   org_score(product, tenant)
#     = sum over employees of per_employee_score(product, employee)
#
# Products that help the most employees naturally float to the top.
# Products targeting rare conditions in this workforce score low even if
# they would be a perfect match for one person.


@dataclass
class OrgScoredProduct:
    """A product scored against a workforce profile, plus population-aware
    reasons. Mirrors `ScoredProduct` but at the org level."""

    product: Product
    score: float
    reasons: list[str]


def _format_population_reason(prefix: str, dimension, total_employees: int) -> str:
    """Build a reason string that names the dimension and shows the
    population reach. `dimension` is a `DimensionPressure` (duck-typed).

    Examples:
      "Targets Mental Illness, affecting 20 of your 30 employees (66.7%)"
      "Addresses Stress factor, affecting 22 of your 30 employees (73.3%)"
    """
    pct = dimension.percent_affected(total_employees)
    return (
        f"{prefix} {dimension.name}, affecting {dimension.total_affected} "
        f"of your {total_employees} employees ({pct}%)"
    )


def score_product_for_organization(
    product: Product,
    workforce: "WorkforceProfile",
) -> OrgScoredProduct:
    """Score one product against the aggregated workforce profile.

    Returns an `OrgScoredProduct` with `score` and population-aware
    `reasons`. Only matches that have non-zero population pressure count.
    """
    score = 0.0
    reasons: list[str] = []

    # Lookup tables by dimension name, so each product condition / factor can
    # find its matching workforce pressure entry in O(1).
    condition_pressure = {dp.name: dp for dp in workforce.conditions}
    factor_pressure = {dp.name: dp for dp in workforce.factors}

    for pc in product.conditions:
        dimension = condition_pressure.get(pc.health_condition)
        if dimension is None:
            continue
        relevance = float(pc.relevance_score)
        contribution = CONDITION_MATCH_BASE * relevance * dimension.pressure_score
        score += contribution
        reasons.append(_format_population_reason("Targets", dimension, workforce.total_employees))

    for pf in product.factors:
        dimension = factor_pressure.get(pf.factor)
        if dimension is None:
            continue
        relevance = float(pf.relevance_score)
        contribution = FACTOR_MATCH_BASE * relevance * dimension.pressure_score
        score += contribution
        # "Addresses <factor> factor, affecting ..." matches the per-employee
        # phrasing convention.
        reasons.append(
            _format_population_reason(
                "Addresses",
                _FactorReason(dimension),
                workforce.total_employees,
            )
        )

    return OrgScoredProduct(product=product, score=round(score, 4), reasons=reasons)


class _FactorReason:
    """Tiny adapter that lets `_format_population_reason` print the factor
    name with the word "factor" appended, while still using the shared
    formatter."""

    def __init__(self, dimension):
        self._d = dimension
        self.name = f"{dimension.name} factor"

    @property
    def total_affected(self) -> int:
        return self._d.total_affected

    def percent_affected(self, total_employees: int) -> float:
        return self._d.percent_affected(total_employees)


def rank_products_for_organization(
    products: Iterable[Product],
    workforce: "WorkforceProfile",
    top_n: int = 10,
) -> list[OrgScoredProduct]:
    """Score and rank products at the org level. Returns top N with score > 0.

    Same shape and behavior as `rank_products` but for the workforce
    aggregate input.
    """
    scored = [score_product_for_organization(product, workforce) for product in products]
    scored = [sp for sp in scored if sp.score > 0]
    scored.sort(key=lambda sp: sp.score, reverse=True)
    return scored[:top_n]
