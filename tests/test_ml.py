"""Tests for the ML layer: predictor loading, aggregation, scoring boost.

The predictor needs `data/model.pkl` to be present. If it is not, the load
returns None and tests that require a real predictor are skipped.
"""

from dataclasses import dataclass, field

import pytest

from app.ml.predictor import (
    CONDITION_LABEL_TO_DB,
    FACTOR_LABEL_TO_DB,
    RiskPredictor,
    aggregate_factor_severity,
)
from app.services.scoring import (
    ML_ALGORITHM_VERSION,
    ML_RISK_PROB_THRESHOLD,
    score_product_for_employee,
)


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


# ---- aggregate_factor_severity ----


def test_aggregate_factor_severity_maps_db_names_to_model_features():
    records = [
        StubHealthRecord(
            factor="Sleep",
            health_condition="Cardiovascular Disease",
            severity="Very Important",
            status="Suffering",
        ),
        StubHealthRecord(
            factor="Stress",
            health_condition="Cardiovascular Disease",
            severity="Important",
            status="At Risk",
        ),
    ]
    out = aggregate_factor_severity(records)
    assert set(out.keys()) <= set(FACTOR_LABEL_TO_DB.keys())
    assert "sleep" in out
    assert "stress" in out
    # Suffering + Very Important > Important + At Risk
    assert out["sleep"] > out["stress"]


def test_aggregate_factor_severity_takes_max_per_factor():
    """If a factor appears in multiple records, we keep the worst severity."""
    records = [
        StubHealthRecord(
            factor="Sleep",
            health_condition="Mental Illness",
            severity="Important",
            status="At Risk",
        ),
        StubHealthRecord(
            factor="Sleep",
            health_condition="Cardiovascular Disease",
            severity="Very Important",
            status="Suffering",
        ),
    ]
    out = aggregate_factor_severity(records)
    # The Very Important + Suffering combo must win.
    assert out["sleep"] >= 0.9


def test_aggregate_factor_severity_ignores_unknown_factors():
    """Unknown DB factors should not affect the model input. Other factors
    still get the population baseline."""
    records = [
        StubHealthRecord(
            factor="MadeUpFactor",
            health_condition="Cancer",
            severity="Important",
            status="At Risk",
        )
    ]
    out = aggregate_factor_severity(records)
    # All 8 known factors should be present at the baseline.
    assert set(out.keys()) == set(FACTOR_LABEL_TO_DB.keys())
    # Every value should equal the baseline since no known factor was reported.
    assert len(set(out.values())) == 1


def test_aggregate_factor_severity_fills_missing_factors_with_baseline():
    """Factors not mentioned in records still appear in the output, at the
    population baseline. This avoids telling the model 'perfectly healthy on
    this factor' when we have no data."""
    records = [
        StubHealthRecord(
            factor="Sleep",
            health_condition="Mental Illness",
            severity="Very Important",
            status="Suffering",
        )
    ]
    out = aggregate_factor_severity(records)
    assert set(out.keys()) == set(FACTOR_LABEL_TO_DB.keys())
    # Sleep was reported and should be high.
    assert out["sleep"] >= 0.9
    # An unreported factor should sit at the baseline.
    assert 0.0 < out["smoke"] < 0.9


# ---- predictor load + predict_risk ----


def test_predictor_loads_or_returns_none_cleanly():
    """Either the model is on disk (returns a RiskPredictor) or it isn't
    (returns None). Both are valid; the API must work in pure rules mode if
    the model is missing."""
    predictor = RiskPredictor.from_disk()
    assert predictor is None or isinstance(predictor, RiskPredictor)


def test_predictor_predicts_six_conditions_with_db_names():
    predictor = RiskPredictor.from_disk()
    if predictor is None:
        pytest.skip("model not trained; run scripts/train_model.py")
    risks = predictor.predict_risk(
        {
            "sleep": 0.1,
            "depression": 0.9,
            "smoke": 0.9,
            "stress": 0.9,
            "movement": 0.1,
            "nutrition": 0.9,
            "wellness": 0.1,
            "obesity": 0.9,
        }
    )
    assert set(risks.keys()) == set(CONDITION_LABEL_TO_DB.values())
    for value in risks.values():
        assert 0.0 <= value <= 1.0


def test_predictor_responds_to_input_changes():
    """A high-risk feature profile should produce at least one larger
    probability than a low-risk profile. Tests that the model is actually
    using its features, not just returning a constant."""
    predictor = RiskPredictor.from_disk()
    if predictor is None:
        pytest.skip("model not trained; run scripts/train_model.py")

    healthy = dict.fromkeys(FACTOR_LABEL_TO_DB, 0.1)
    healthy["wellness"] = 0.9
    sick = dict.fromkeys(FACTOR_LABEL_TO_DB, 0.9)
    sick["wellness"] = 0.1

    risks_healthy = predictor.predict_risk(healthy)
    risks_sick = predictor.predict_risk(sick)
    assert max(risks_sick.values()) > max(risks_healthy.values())


# ---- scoring with risk_scores ----


def test_scoring_ignores_risk_below_threshold():
    """Risk probabilities below the threshold should not boost a product."""
    product = StubProduct(
        conditions=[StubProductCondition("Cancer", 1.0)],
    )
    records = [
        StubHealthRecord(
            factor="Sleep",
            health_condition="Type 2 Diabetes",
            severity="Important",
            status="At Risk",
        )
    ]
    low_risk = {"Cancer": ML_RISK_PROB_THRESHOLD - 0.1}

    result = score_product_for_employee(product, records, risk_scores=low_risk)
    assert result.score == 0.0
    assert result.reasons == []


def test_scoring_boosts_when_risk_above_threshold():
    """High predicted risk on a condition the employee does not yet have should
    boost products targeting that condition and add an ML reason."""
    product = StubProduct(
        conditions=[StubProductCondition("Cancer", 1.0)],
    )
    records = [
        StubHealthRecord(
            factor="Sleep",
            health_condition="Type 2 Diabetes",
            severity="Important",
            status="At Risk",
        )
    ]
    high_risk = {"Cancer": 0.9}

    result = score_product_for_employee(product, records, risk_scores=high_risk)
    assert result.score > 0.0
    assert any("ML predicts" in r for r in result.reasons)


def test_scoring_does_not_double_count_when_condition_already_in_records():
    """If the employee already has the condition, no ML boost should be added
    on top (it is already a direct condition match)."""
    product = StubProduct(
        conditions=[StubProductCondition("Cancer", 1.0)],
    )
    records = [
        StubHealthRecord(
            factor="Sleep",
            health_condition="Cancer",
            severity="Important",
            status="Suffering",
        )
    ]
    high_risk = {"Cancer": 0.9}

    with_risk = score_product_for_employee(product, records, risk_scores=high_risk)
    without_risk = score_product_for_employee(product, records, risk_scores=None)
    assert with_risk.score == without_risk.score
    assert not any("ML predicts" in r for r in with_risk.reasons)


def test_ml_algorithm_version_constant_is_distinct():
    assert ML_ALGORITHM_VERSION == "rules-ml-v1"
