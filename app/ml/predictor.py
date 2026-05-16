"""Load the trained risk-prediction model and serve predictions.

The model is the multi-output RandomForest produced by
`scripts/train_model.py`. It takes the 8 factor severity scores and returns
a probability for each of the 6 chronic conditions.

The trained model lives at `data/model.pkl`. If it is missing (someone has
not trained yet), the predictor logs a warning and returns zero probabilities
so the recommender can keep working in pure rules mode.

The DB stores factor and condition names in human-readable form
("Cardiovascular Disease"). The model uses snake_case labels. Two mapping
tables here bridge the two namespaces.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from app.models import HealthRecord

logger = logging.getLogger("nytia.ml")

MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "model.pkl"
MODEL_VERSION = "rf-v1"

# Map the DB-side factor names to the model's input feature names.
FACTOR_LABEL_TO_DB = {
    "sleep": "Sleep",
    "depression": "Depression",
    "smoke": "Smoke",
    "stress": "Stress",
    "movement": "Movement",
    "nutrition": "Nutrition",
    "wellness": "Wellness",
    "obesity": "Obesity",
}

# Map the model's output label names to the DB condition names.
CONDITION_LABEL_TO_DB = {
    "cardiovascular_disease": "Cardiovascular Disease",
    "type_2_diabetes": "Type 2 Diabetes",
    "chronic_kidney_disease": "Chronic Kidney Disease",
    "cancer": "Cancer",
    "mental_illness": "Mental Illness",
    "osteoporosis": "Osteoporosis",
}

# Inverse: DB factor name -> model feature name.
DB_TO_FACTOR_LABEL = {v: k for k, v in FACTOR_LABEL_TO_DB.items()}

# Severity weight used when collapsing raw health records to a single severity
# score per factor (0..1).
_SEVERITY_SCORE = {
    "Very Important": 0.9,
    "Important": 0.6,
}
_STATUS_BUMP = {
    "Suffering": 0.15,
    "At Risk": 0.0,
}

# When a factor is not present in an employee's records we cannot tell whether
# they are healthy on that factor or simply unreported. The training data has
# mean factor severity of about 0.4, so we use that as the population prior.
_POPULATION_BASELINE = 0.4


class RiskPredictor:
    """Wraps the trained model. Thread-safe to load once and call many times."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.model = payload["model"]
        self.factors: list[str] = payload["factors"]
        self.conditions: list[str] = payload["conditions"]
        self.version: str = payload.get("version", MODEL_VERSION)
        self.metrics: dict[str, Any] = payload.get("metrics", {})

    @classmethod
    def from_disk(cls, path: Path = MODEL_PATH) -> RiskPredictor | None:
        """Load the pickled model from disk. Return None if it does not exist."""
        if not path.exists():
            logger.warning(
                "ml model file missing; predictor disabled",
                extra={"path": str(path)},
            )
            return None
        try:
            payload = joblib.load(path)
        except Exception:
            logger.exception("failed to load ml model", extra={"path": str(path)})
            return None
        logger.info(
            "ml model loaded",
            extra={
                "path": str(path),
                "version": payload.get("version"),
                "n_features": len(payload.get("factors", [])),
                "n_targets": len(payload.get("conditions", [])),
            },
        )
        return cls(payload)

    def predict_risk(self, factor_severity: dict[str, float]) -> dict[str, float]:
        """Return a probability per DB-condition-name.

        `factor_severity` maps the model's feature names (snake_case) to a
        value in [0, 1]. Missing features are treated as 0.
        """
        feature_row = pd.DataFrame(
            [[factor_severity.get(name, 0.0) for name in self.factors]],
            columns=self.factors,
        )
        proba_list = self.model.predict_proba(feature_row)
        out: dict[str, float] = {}
        for i, model_label in enumerate(self.conditions):
            # Multi-output returns one (n_samples, n_classes) array per target.
            row_probs = proba_list[i][0]
            # column 1 = P(label = 1); fall back to 0 if model only saw one class.
            prob = float(row_probs[1]) if len(row_probs) > 1 else 0.0
            db_name = CONDITION_LABEL_TO_DB.get(model_label, model_label)
            out[db_name] = prob
        return out


# ----- module-level lazy singleton -----

_predictor: RiskPredictor | None = None
_predictor_lock = threading.Lock()
_predictor_loaded = False


def get_predictor() -> RiskPredictor | None:
    """Return the loaded predictor, or None if no model is available.

    Loads from disk on first call. Subsequent calls reuse the cached instance.
    Safe to call from request handlers.
    """
    global _predictor, _predictor_loaded
    if _predictor_loaded:
        return _predictor
    with _predictor_lock:
        if not _predictor_loaded:
            _predictor = RiskPredictor.from_disk()
            _predictor_loaded = True
    return _predictor


def aggregate_factor_severity(records: Iterable[HealthRecord]) -> dict[str, float]:
    """Collapse a list of health records into a per-factor severity score in [0, 1].

    The model expects one number per factor. The DB has multiple records per
    employee, sometimes more than one row touching the same factor. For each
    factor we take the worst (max) severity reported.

    Factors not present in any record fall back to the population baseline
    (~0.4) instead of 0. A zero would tell the model "this employee is
    perfectly healthy on this factor", which is a stronger claim than the
    absence of a record actually supports.
    """
    severity_by_factor: dict[str, float] = dict.fromkeys(FACTOR_LABEL_TO_DB, _POPULATION_BASELINE)
    for rec in records:
        model_factor = DB_TO_FACTOR_LABEL.get(rec.factor)
        if model_factor is None:
            continue
        score = _SEVERITY_SCORE.get(rec.severity, 0.5) + _STATUS_BUMP.get(rec.status, 0.0)
        score = max(0.0, min(1.0, score))
        if score > severity_by_factor[model_factor]:
            severity_by_factor[model_factor] = score
    return severity_by_factor
