"""Train a risk classifier on the synthetic training data.

A single multi-output RandomForest predicts the probability of each of the 6
conditions from the 8 contributing factors. RandomForestClassifier handles
multi-output natively, which keeps the serving code simple.

Run:
    uv run python scripts/train_model.py

Inputs:
    data/synthetic_training.csv (from scripts/generate_training_data.py)

Outputs:
    data/model.pkl              joblib-pickled model + metadata
    data/model_metrics.json     per-condition precision/recall/ROC-AUC

The model is intentionally small (n_estimators=100) so it loads fast at API
startup.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import train_test_split

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_PATH = DATA_DIR / "synthetic_training.csv"
MODEL_PATH = DATA_DIR / "model.pkl"
METRICS_PATH = DATA_DIR / "model_metrics.json"

FACTORS = [
    "sleep",
    "depression",
    "smoke",
    "stress",
    "movement",
    "nutrition",
    "wellness",
    "obesity",
]

CONDITIONS = [
    "cardiovascular_disease",
    "type_2_diabetes",
    "chronic_kidney_disease",
    "cancer",
    "mental_illness",
    "osteoporosis",
]

MODEL_VERSION = "rf-v1"


def main() -> None:
    if not CSV_PATH.exists():
        raise SystemExit(
            f"training csv not found at {CSV_PATH}.\n"
            "run `uv run python scripts/generate_training_data.py` first."
        )

    df = pd.read_csv(CSV_PATH)
    print(f"loaded {len(df):,} rows from {CSV_PATH.relative_to(Path.cwd())}")

    x = df[FACTORS]
    y = df[CONDITIONS]

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=None
    )

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
    )
    print("training...")
    model.fit(x_train, y_train)

    # predict_proba on multi-output returns a list of arrays (one per label).
    # Each entry is (n_samples, 2). Take column 1 (P(label=1)).
    proba_list = model.predict_proba(x_test)
    preds = model.predict(x_test)

    metrics: dict[str, dict[str, float]] = {}
    for i, condition in enumerate(CONDITIONS):
        y_true = y_test[condition].to_numpy()
        y_pred = preds[:, i]
        y_proba = proba_list[i][:, 1]
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average="binary", zero_division=0
        )
        try:
            auc = roc_auc_score(y_true, y_proba)
        except ValueError:
            auc = float("nan")
        metrics[condition] = {
            "precision": round(float(precision), 3),
            "recall": round(float(recall), 3),
            "f1": round(float(f1), 3),
            "roc_auc": round(float(auc), 3),
            "positive_rate": round(float(y_true.mean()), 3),
        }

    payload = {
        "model": model,
        "factors": FACTORS,
        "conditions": CONDITIONS,
        "version": MODEL_VERSION,
        "metrics": metrics,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, MODEL_PATH)
    METRICS_PATH.write_text(
        json.dumps(
            {"version": MODEL_VERSION, "metrics": metrics},
            indent=2,
        )
    )

    print(f"\nsaved model to {MODEL_PATH.relative_to(Path.cwd())}")
    print(f"saved metrics to {METRICS_PATH.relative_to(Path.cwd())}")
    print("\nper-condition metrics:")
    width = max(len(c) for c in CONDITIONS)
    header = f"  {'condition'.ljust(width)}  prec   rec    f1    auc   pos"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for condition, m in metrics.items():
        print(
            f"  {condition.ljust(width)}  "
            f"{m['precision']:.3f}  {m['recall']:.3f}  "
            f"{m['f1']:.3f}  {m['roc_auc']:.3f}  {m['positive_rate']:.3f}"
        )


if __name__ == "__main__":
    main()
