"""Tests for the org-level scoring + ranking functions.

Stubs the Product / ProductCondition / ProductFactor models and builds
small in-memory WorkforceProfile values, then exercises:

- A product matching the highest-pressure dimension scores highest.
- Reasons include the population count and percentage from the workforce.
- An empty workforce yields no recommendations.
- top_n is respected.
- Zero-score products are excluded.
- A product matching both a condition and a factor sums the contributions.
"""

from dataclasses import dataclass, field

from app.services.org_aggregator import DimensionPressure, WorkforceProfile
from app.services.scoring import (
    CONDITION_MATCH_BASE,
    FACTOR_MATCH_BASE,
    ORG_ALGORITHM_VERSION,
    rank_products_for_organization,
    score_product_for_organization,
)

# ----- stub product types (duck-typed to the real ORM models) -----


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


# ----- helpers -----


def _profile(
    total: int,
    conditions: list[DimensionPressure] | None = None,
    factors: list[DimensionPressure] | None = None,
) -> WorkforceProfile:
    return WorkforceProfile(
        tenant_id="T_TEST",
        total_employees=total,
        conditions=conditions or [],
        factors=factors or [],
    )


def _cond(name: str, pressure: float, suffering: int = 0, at_risk: int = 0) -> DimensionPressure:
    return DimensionPressure(
        name=name,
        suffering_count=suffering,
        at_risk_count=at_risk,
        pressure_score=pressure,
    )


# ----- constant -----


def test_org_algorithm_version_is_distinct():
    assert ORG_ALGORITHM_VERSION == "org-rules-v1"


# ----- ranking: biggest population pressure wins -----


def test_product_matching_biggest_population_pressure_scores_highest():
    """Two products targeting two different conditions. The one whose
    target has higher workforce pressure must rank first."""
    workforce = _profile(
        total=30,
        conditions=[
            _cond("Mental Illness", pressure=50.0, suffering=15, at_risk=5),
            _cond("Osteoporosis", pressure=5.0, suffering=2, at_risk=0),
        ],
    )

    mental_product = StubProduct(
        id=1,
        name="Mental Health Therapy",
        conditions=[StubProductCondition("Mental Illness", 1.0)],
    )
    bone_product = StubProduct(
        id=2,
        name="Bone Health Program",
        conditions=[StubProductCondition("Osteoporosis", 1.0)],
    )

    results = rank_products_for_organization([mental_product, bone_product], workforce, top_n=10)

    assert [r.product.name for r in results] == ["Mental Health Therapy", "Bone Health Program"]
    assert results[0].score > results[1].score


# ----- reasons -----


def test_reasons_include_population_count_and_percentage_for_condition():
    workforce = _profile(
        total=30,
        conditions=[_cond("Mental Illness", pressure=50.0, suffering=15, at_risk=5)],
    )
    product = StubProduct(
        conditions=[StubProductCondition("Mental Illness", 1.0)],
    )

    scored = score_product_for_organization(product, workforce)

    assert len(scored.reasons) == 1
    reason = scored.reasons[0]
    assert "Mental Illness" in reason
    assert "20 of your 30 employees" in reason  # 15 + 5
    assert "66.7%" in reason
    assert reason.startswith("Targets ")


def test_reasons_include_population_count_and_percentage_for_factor():
    workforce = _profile(
        total=30,
        factors=[_cond("Stress", pressure=40.0, suffering=12, at_risk=10)],
    )
    product = StubProduct(
        factors=[StubProductFactor("Stress", 1.0)],
    )

    scored = score_product_for_organization(product, workforce)

    assert len(scored.reasons) == 1
    reason = scored.reasons[0]
    assert "Stress factor" in reason
    assert "22 of your 30 employees" in reason
    assert "73.3%" in reason
    assert reason.startswith("Addresses ")


# ----- empty workforce -----


def test_empty_workforce_yields_no_recommendations():
    workforce = _profile(total=0, conditions=[], factors=[])
    product = StubProduct(
        conditions=[StubProductCondition("Mental Illness", 1.0)],
    )

    scored = score_product_for_organization(product, workforce)
    assert scored.score == 0.0
    assert scored.reasons == []

    ranked = rank_products_for_organization([product], workforce, top_n=10)
    assert ranked == []


# ----- top_n -----


def test_top_n_is_respected():
    workforce = _profile(
        total=30,
        conditions=[_cond("Mental Illness", pressure=50.0, suffering=15, at_risk=5)],
    )
    # Five different products all targeting the same condition with
    # decreasing relevance, so their scores are strictly ordered.
    products = [
        StubProduct(
            id=i,
            name=f"P{i}",
            conditions=[StubProductCondition("Mental Illness", relevance)],
        )
        for i, relevance in enumerate([1.0, 0.9, 0.8, 0.7, 0.6], start=1)
    ]

    ranked = rank_products_for_organization(products, workforce, top_n=3)

    assert len(ranked) == 3
    assert [r.product.name for r in ranked] == ["P1", "P2", "P3"]


# ----- zero-score exclusion -----


def test_zero_score_products_excluded():
    workforce = _profile(
        total=30,
        conditions=[_cond("Mental Illness", pressure=50.0, suffering=20, at_risk=0)],
    )
    # The non-matching product targets a condition the workforce doesn't have.
    matching = StubProduct(
        id=1,
        name="Match",
        conditions=[StubProductCondition("Mental Illness", 1.0)],
    )
    non_matching = StubProduct(
        id=2,
        name="NoMatch",
        conditions=[StubProductCondition("Osteoporosis", 1.0)],
    )

    ranked = rank_products_for_organization([matching, non_matching], workforce, top_n=10)

    assert len(ranked) == 1
    assert ranked[0].product.name == "Match"


# ----- mixed condition + factor product -----


def test_mixed_product_sums_condition_and_factor_contributions():
    """One product tags BOTH a condition and a factor that the workforce
    has. The score must be the sum of both contributions and both reasons
    must appear."""
    workforce = _profile(
        total=30,
        conditions=[_cond("Type 2 Diabetes", pressure=40.0, suffering=20, at_risk=0)],
        factors=[_cond("Nutrition", pressure=20.0, suffering=10, at_risk=5)],
    )

    product = StubProduct(
        name="Nutrition Counseling",
        conditions=[StubProductCondition("Type 2 Diabetes", 1.0)],
        factors=[StubProductFactor("Nutrition", 1.0)],
    )

    scored = score_product_for_organization(product, workforce)

    expected_condition = CONDITION_MATCH_BASE * 1.0 * 40.0  # 80.0
    expected_factor = FACTOR_MATCH_BASE * 1.0 * 20.0  # 30.0
    expected_total = expected_condition + expected_factor  # 110.0

    assert scored.score == round(expected_total, 4)
    assert len(scored.reasons) == 2
    assert any("Type 2 Diabetes" in r for r in scored.reasons)
    assert any("Nutrition factor" in r for r in scored.reasons)


# ----- math sanity: pressure linearity -----


def test_doubling_pressure_doubles_score():
    """Score is linear in pressure_score. Double the pressure on the same
    condition, the score should double too."""
    product = StubProduct(
        conditions=[StubProductCondition("Mental Illness", 1.0)],
    )

    low = _profile(total=10, conditions=[_cond("Mental Illness", pressure=5.0, suffering=5)])
    high = _profile(total=10, conditions=[_cond("Mental Illness", pressure=10.0, suffering=10)])

    score_low = score_product_for_organization(product, low).score
    score_high = score_product_for_organization(product, high).score

    assert score_high == round(2 * score_low, 4)
