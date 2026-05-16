"""Tests for the scoring function.

These tests use simple stub objects instead of real SQLAlchemy models
because the scoring function only reads attributes, never touches the DB.
"""

from dataclasses import dataclass, field

import pytest

from app.services.scoring import (
    CONDITION_MATCH_BASE,
    SEVERITY_WEIGHT,
    STATUS_WEIGHT,
    rank_products,
    score_product_for_employee,
)

# ---------- Stub objects (mimic the real models) ----------


@dataclass
class StubProductCondition:
    health_condition: str
    relevance_score: float


@dataclass
class StubProductFactor:
    factor: str
    relevance_score: float


@dataclass
class StubProduct:
    id: int = 1
    name: str = "Test Product"
    conditions: list = field(default_factory=list)
    factors: list = field(default_factory=list)


@dataclass
class StubHealthRecord:
    factor: str
    health_condition: str
    severity: str
    status: str


# ---------- Tests ----------


def test_no_matches_returns_zero_score():
    """If product targets things the employee does not have, score is 0."""
    product = StubProduct(
        conditions=[StubProductCondition("Cancer", 1.0)],
        factors=[StubProductFactor("Stress", 1.0)],
    )
    records = [
        StubHealthRecord(
            factor="Sleep",
            health_condition="Type 2 Diabetes",
            severity="Important",
            status="At Risk",
        )
    ]

    result = score_product_for_employee(product, records)

    assert result.score == 0.0
    assert result.reasons == []


def test_single_condition_match_calculates_correct_score():
    """Verify the exact math for a condition match.

    Formula: CONDITION_MATCH_BASE * relevance * severity_weight * status_weight
    Expected: 2.0 * 1.0 * 1.5 * 1.2 = 3.6
    """
    product = StubProduct(
        conditions=[StubProductCondition("Type 2 Diabetes", 1.0)],
    )
    records = [
        StubHealthRecord(
            factor="Sleep",
            health_condition="Type 2 Diabetes",
            severity="Very Important",
            status="Suffering",
        )
    ]

    result = score_product_for_employee(product, records)

    expected = (
        CONDITION_MATCH_BASE * 1.0 * SEVERITY_WEIGHT["Very Important"] * STATUS_WEIGHT["Suffering"]
    )
    assert result.score == pytest.approx(expected)
    assert result.score == pytest.approx(3.6)
    assert len(result.reasons) == 1
    assert "Type 2 Diabetes" in result.reasons[0]


def test_single_factor_match_calculates_correct_score():
    """Factor match uses FACTOR_MATCH_BASE (1.5), lighter than condition match.

    Expected: 1.5 * 1.0 * 1.0 * 1.0 = 1.5
    (Important severity = 1.0, At Risk status = 1.0)
    """
    product = StubProduct(
        factors=[StubProductFactor("Sleep", 1.0)],
    )
    records = [
        StubHealthRecord(
            factor="Sleep",
            health_condition="Type 2 Diabetes",
            severity="Important",
            status="At Risk",
        )
    ]

    result = score_product_for_employee(product, records)

    assert result.score == pytest.approx(1.5)
    assert "Sleep" in result.reasons[0]
    assert "factor" in result.reasons[0]


def test_condition_match_scores_higher_than_factor_match():
    """Condition match should always beat factor match for same employee profile.

    Core to the algorithm: treating diagnosed conditions is more urgent than
    addressing lifestyle factors.
    """
    employee_records = [
        StubHealthRecord(
            factor="Stress",
            health_condition="Cardiovascular Disease",
            severity="Important",
            status="At Risk",
        )
    ]

    product_targeting_condition = StubProduct(
        conditions=[StubProductCondition("Cardiovascular Disease", 1.0)],
    )
    product_targeting_factor = StubProduct(
        factors=[StubProductFactor("Stress", 1.0)],
    )

    score_condition = score_product_for_employee(
        product_targeting_condition, employee_records
    ).score
    score_factor = score_product_for_employee(product_targeting_factor, employee_records).score

    assert score_condition > score_factor


def test_severity_very_important_scores_higher_than_important():
    """Same product, same employee, only severity changes. Very Important wins."""
    product = StubProduct(
        conditions=[StubProductCondition("Cancer", 1.0)],
    )

    important_record = [
        StubHealthRecord(
            factor="Sleep",
            health_condition="Cancer",
            severity="Important",
            status="Suffering",
        )
    ]
    very_important_record = [
        StubHealthRecord(
            factor="Sleep",
            health_condition="Cancer",
            severity="Very Important",
            status="Suffering",
        )
    ]

    score_low = score_product_for_employee(product, important_record).score
    score_high = score_product_for_employee(product, very_important_record).score

    assert score_high > score_low


def test_suffering_status_scores_higher_than_at_risk():
    """Suffering employees get heavier weighting than At Risk."""
    product = StubProduct(
        conditions=[StubProductCondition("Cancer", 1.0)],
    )

    at_risk = [
        StubHealthRecord(
            factor="Sleep",
            health_condition="Cancer",
            severity="Important",
            status="At Risk",
        )
    ]
    suffering = [
        StubHealthRecord(
            factor="Sleep",
            health_condition="Cancer",
            severity="Important",
            status="Suffering",
        )
    ]

    score_at_risk = score_product_for_employee(product, at_risk).score
    score_suffering = score_product_for_employee(product, suffering).score

    assert score_suffering > score_at_risk


def test_combined_condition_and_factor_match_sums_scores():
    """If a product matches both a condition AND a factor, scores stack."""
    product = StubProduct(
        conditions=[StubProductCondition("Type 2 Diabetes", 1.0)],
        factors=[StubProductFactor("Nutrition", 1.0)],
    )
    records = [
        StubHealthRecord(
            factor="Nutrition",
            health_condition="Type 2 Diabetes",
            severity="Important",
            status="At Risk",
        )
    ]

    result = score_product_for_employee(product, records)

    # condition: 2.0 * 1.0 * 1.0 * 1.0 = 2.0
    # factor:    1.5 * 1.0 * 1.0 * 1.0 = 1.5
    # total = 3.5
    assert result.score == pytest.approx(3.5)
    assert len(result.reasons) == 2


def test_rank_products_excludes_zero_score_products():
    """Products that don't match anything should not appear in results."""
    matching = StubProduct(
        id=1,
        name="Matching",
        conditions=[StubProductCondition("Cancer", 1.0)],
    )
    non_matching = StubProduct(
        id=2,
        name="Not Matching",
        conditions=[StubProductCondition("Osteoporosis", 1.0)],
    )
    records = [
        StubHealthRecord(
            factor="Sleep",
            health_condition="Cancer",
            severity="Important",
            status="Suffering",
        )
    ]

    results = rank_products([matching, non_matching], records, top_n=10)

    assert len(results) == 1
    assert results[0].product.name == "Matching"


def test_rank_products_respects_top_n():
    """Only top N products should be returned, ordered by score descending."""
    products = [
        StubProduct(
            id=i,
            name=f"Product {i}",
            conditions=[StubProductCondition("Cancer", float(i) / 10)],
        )
        for i in range(1, 6)
    ]
    records = [
        StubHealthRecord(
            factor="Sleep",
            health_condition="Cancer",
            severity="Important",
            status="Suffering",
        )
    ]

    results = rank_products(products, records, top_n=3)

    assert len(results) == 3
    assert results[0].product.id == 5  # highest relevance
