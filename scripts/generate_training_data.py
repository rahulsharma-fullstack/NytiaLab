"""Generate synthetic training data for the ML risk classifier.

Used until the teammate delivers real synthetic data. The generated dataset
contains 5,000 rows. Inputs are the 8 contributing factors (numeric severity
scores 0-1). Labels are the 6 chronic conditions (binary: has risk / does not).

Risk is generated from a hand-tuned set of "biological-ish" rules so the
model has real signal to learn:

- Cardiovascular Disease: rises with stress, smoke, obesity, poor sleep, poor nutrition.
- Type 2 Diabetes: rises with obesity, poor nutrition, low movement.
- Chronic Kidney Disease: rises with poor nutrition, obesity (proxy for T2D pathway).
- Cancer: rises with smoke, obesity, depression.
- Mental Illness: rises with depression, stress, poor sleep, low wellness.
- Osteoporosis: rises with low movement, poor nutrition, age proxy via wellness.

Each rule sums weighted factors, passes through a sigmoid, and a Bernoulli draw
decides the label. Random noise is added so the classifier has to generalise
instead of memorise.

Run:
    uv run python scripts/generate_training_data.py
Output:
    data/synthetic_training.csv
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import pandas as pd

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_PATH = OUTPUT_DIR / "synthetic_training.csv"
N_ROWS = 5000
RANDOM_SEED = 42

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


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def risk_for_condition(condition: str, f: dict[str, float]) -> float:
    """Hand-tuned rule producing a probability in [0, 1] for one condition.

    Higher factor value = worse state (e.g. high stress, high smoke).
    `wellness` is inverted internally because high wellness is good.
    """
    bad_wellness = 1 - f["wellness"]

    if condition == "cardiovascular_disease":
        z = (
            -2.5
            + 1.6 * f["stress"]
            + 2.0 * f["smoke"]
            + 1.5 * f["obesity"]
            + 1.2 * (1 - f["sleep"])
            + 1.0 * f["nutrition"]
        )
    elif condition == "type_2_diabetes":
        z = -2.8 + 2.2 * f["obesity"] + 1.8 * f["nutrition"] + 1.4 * (1 - f["movement"])
    elif condition == "chronic_kidney_disease":
        z = -3.0 + 1.8 * f["nutrition"] + 1.4 * f["obesity"] + 0.8 * f["stress"]
    elif condition == "cancer":
        z = -3.2 + 2.2 * f["smoke"] + 1.2 * f["obesity"] + 0.8 * f["depression"]
    elif condition == "mental_illness":
        z = (
            -2.0
            + 2.3 * f["depression"]
            + 1.6 * f["stress"]
            + 1.0 * (1 - f["sleep"])
            + 1.0 * bad_wellness
        )
    elif condition == "osteoporosis":
        z = -3.0 + 2.0 * (1 - f["movement"]) + 1.4 * f["nutrition"] + 1.0 * bad_wellness
    else:
        raise ValueError(f"unknown condition: {condition}")

    # Small noise so the labels are not perfectly deterministic.
    z += random.gauss(0, 0.4)
    return sigmoid(z)


def generate_row(rng: random.Random) -> dict[str, float]:
    """Generate one row of factor inputs and condition labels."""
    # Factors as continuous 0-1 severity scores. Mix of distributions so the
    # population is not all "bad" or all "good".
    factors = {name: rng.betavariate(2, 3) for name in FACTORS}

    # Wellness is inversely correlated with depression to be a bit realistic.
    factors["wellness"] = max(0.0, min(1.0, 1.0 - 0.6 * factors["depression"] + rng.gauss(0, 0.1)))

    row: dict[str, float] = dict(factors)
    for condition in CONDITIONS:
        prob = risk_for_condition(condition, factors)
        row[condition] = 1 if rng.random() < prob else 0
    return row


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(RANDOM_SEED)
    random.seed(RANDOM_SEED)

    rows = [generate_row(rng) for _ in range(N_ROWS)]
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"wrote {len(df):,} rows to {OUTPUT_PATH.relative_to(Path.cwd())}")
    print("\nfactor summary:")
    print(df[FACTORS].describe().round(3))
    print("\ncondition prevalence:")
    print((df[CONDITIONS].mean() * 100).round(1).astype(str) + "%")


if __name__ == "__main__":
    main()
