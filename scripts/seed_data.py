"""Seed the database with sample data for development.

Run this from the project root:
    uv run python scripts/seed_data.py

This deletes existing data and reinserts a fresh sample. Idempotent.

Structure:
- 4 tenants:
    T_NYTIA_DEMO  : holds the original 8 employees (existing per-employee demo)
    T_IBM         : 30 employees, stress + sleep + mental health profile
    T_MICROSOFT   : 30 employees, obesity + nutrition + diabetes profile
    T_ACME        : 30 employees, older workforce, CVD + osteoporosis profile
- 98 employees total
- ~2-3 health records per employee
- 12 products (unchanged)

Health record generation for the new tenants uses a seeded
random.Random(42) so the demo dataset is deterministic.
"""

import random
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

# Allow running this file directly with `uv run python scripts/seed_data.py`.
# The project root must be on sys.path before importing from `app`.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy.orm import Session  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Employee,
    HealthRecord,
    Product,
    ProductCondition,
    ProductFactor,
    Recommendation,
    Tenant,
)

SEED = 42
DEFAULT_RECORD_DATE = date(2026, 1, 3)


# ----- Tenants -----

TENANTS = [
    {"id": "T_NYTIA_DEMO", "name": "Nytia Demo"},
    {"id": "T_IBM", "name": "IBM"},
    {"id": "T_MICROSOFT", "name": "Microsoft"},
    {"id": "T_ACME", "name": "Acme Corp"},
]


# ----- Tenant profiles -----
# Each profile is a weighted list of (factor, condition, severity, status, value, unit)
# tuples. Generators pick from this list when synthesising records for a new
# employee. Severities and statuses are drawn so the population skews towards
# the tenant's "story" but is not uniform.

IBM_PROFILE = [
    # (factor, condition, severity, status, value, unit, weight)
    ("Sleep", "Mental Illness", "Very Important", "Suffering", "5.5", "hours", 4),
    ("Sleep", "Cardiovascular Disease", "Important", "At Risk", "6.0", "hours", 2),
    ("Stress", "Mental Illness", "Very Important", "Suffering", "78", "score", 4),
    ("Stress", "Cardiovascular Disease", "Important", "At Risk", "72", "score", 3),
    ("Depression", "Mental Illness", "Very Important", "Suffering", "65", "score", 3),
    ("Depression", "Mental Illness", "Important", "At Risk", "48", "score", 2),
    ("Wellness", "Mental Illness", "Important", "At Risk", "42", "score", 2),
    ("Nutrition", "Cardiovascular Disease", "Important", "At Risk", "60", "score", 1),
]

MICROSOFT_PROFILE = [
    ("Obesity", "Type 2 Diabetes", "Very Important", "Suffering", "88", "score", 4),
    ("Obesity", "Cardiovascular Disease", "Important", "At Risk", "76", "score", 3),
    ("Nutrition", "Type 2 Diabetes", "Very Important", "Suffering", "62", "score", 3),
    ("Nutrition", "Chronic Kidney Disease", "Important", "At Risk", "55", "score", 2),
    ("Movement", "Type 2 Diabetes", "Important", "Suffering", "3.2", "hours", 3),
    ("Movement", "Cardiovascular Disease", "Important", "At Risk", "4.0", "hours", 2),
    ("Stress", "Cardiovascular Disease", "Important", "At Risk", "65", "score", 1),
    ("Sleep", "Mental Illness", "Important", "At Risk", "6.5", "hours", 1),
]

ACME_PROFILE = [
    ("Movement", "Osteoporosis", "Very Important", "Suffering", "2.5", "hours", 4),
    ("Movement", "Cardiovascular Disease", "Important", "Suffering", "3.0", "hours", 3),
    ("Nutrition", "Chronic Kidney Disease", "Important", "Suffering", "58", "score", 3),
    ("Nutrition", "Cardiovascular Disease", "Important", "At Risk", "62", "score", 2),
    ("Smoke", "Cardiovascular Disease", "Very Important", "At Risk", "85", "score", 2),
    ("Smoke", "Cancer", "Important", "At Risk", "70", "score", 2),
    ("Obesity", "Cardiovascular Disease", "Important", "Suffering", "82", "score", 2),
    ("Wellness", "Osteoporosis", "Important", "At Risk", "55", "score", 1),
]

REGIONS_BY_TENANT = {
    "T_IBM": ["Toronto", "North York", "Mississauga", "Waterloo", "Hamilton"],
    "T_MICROSOFT": ["Vancouver", "Burnaby", "Surrey", "Richmond", "Coquitlam"],
    "T_ACME": ["Calgary", "Edmonton", "Red Deer", "Lethbridge", "Medicine Hat"],
}

LEGACY_TENANT_STRING = {
    "T_NYTIA_DEMO": "NYTIA",
    "T_IBM": "IBM",
    "T_MICROSOFT": "Microsoft",
    "T_ACME": "Acme",
}

NEW_TENANT_SPECS = [
    {"tenant_id": "T_IBM", "prefix": "E_IBM_", "profile": IBM_PROFILE, "count": 30},
    {"tenant_id": "T_MICROSOFT", "prefix": "E_MS_", "profile": MICROSOFT_PROFILE, "count": 30},
    {"tenant_id": "T_ACME", "prefix": "E_ACME_", "profile": ACME_PROFILE, "count": 30},
]


# ----- Clearing -----


def clear_all_data(db: Session) -> None:
    """Delete all rows from all tables. Order matters for foreign keys."""
    print("Clearing existing data...")
    db.query(Recommendation).delete()
    db.query(ProductCondition).delete()
    db.query(ProductFactor).delete()
    db.query(HealthRecord).delete()
    db.query(Product).delete()
    db.query(Employee).delete()
    db.query(Tenant).delete()
    db.commit()


# ----- Tenants -----


def seed_tenants(db: Session) -> None:
    print("Seeding tenants...")
    db.add_all([Tenant(id=t["id"], name=t["name"]) for t in TENANTS])
    db.commit()


# ----- Original 8 employees (preserved exactly) -----


def seed_original_employees_and_records(db: Session) -> None:
    """Insert the 8 demo employees and their 12 health records exactly as
    they have always been, but now linked to T_NYTIA_DEMO."""
    print("Seeding original 8 demo employees + 12 records...")

    legacy_employees = [
        ("E0001", "Waterloo Wellington"),
        ("E0002", "Central East"),
        ("E0003", "Central West"),
        ("E0004", "South East"),
        ("E0005", "North Simcoe"),
        ("E0006", "Erie St. Clair"),
        ("E0007", "Waterloo Wellington"),
        ("E0008", "North West"),
    ]
    db.add_all(
        [
            Employee(
                id=eid,
                region=region,
                tenant="NYTIA",
                tenant_id="T_NYTIA_DEMO",
            )
            for eid, region in legacy_employees
        ]
    )
    db.commit()

    legacy_records = [
        # E0001 - Sleep + CVD heavy
        (
            "E0001",
            "Sleep",
            "Cardiovascular Disease",
            "Suffering",
            "Very Important",
            "5.7",
            "hours",
            "0.25",
        ),
        (
            "E0001",
            "Stress",
            "Cardiovascular Disease",
            "Suffering",
            "Important",
            "69",
            "score",
            "0.23",
        ),
        # E0002 - multi-issue
        (
            "E0002",
            "Depression",
            "Mental Illness",
            "Suffering",
            "Very Important",
            "49",
            "score",
            "0.20",
        ),
        (
            "E0002",
            "Smoke",
            "Cardiovascular Disease",
            "At Risk",
            "Very Important",
            "99",
            "score",
            "0.17",
        ),
        ("E0002", "Nutrition", "Type 2 Diabetes", "Suffering", "Important", "54", "score", "0.32"),
        # E0003 - preventive
        (
            "E0003",
            "Nutrition",
            "Chronic Kidney Disease",
            "At Risk",
            "Important",
            "76",
            "score",
            "0.28",
        ),
        # E0004 - severe mental health
        (
            "E0004",
            "Depression",
            "Mental Illness",
            "Suffering",
            "Very Important",
            "86",
            "score",
            "0.21",
        ),
        # E0005 - cancer
        ("E0005", "Obesity", "Cancer", "Suffering", "Very Important", "60", "score", "0.18"),
        # E0006 - diabetes
        ("E0006", "Movement", "Type 2 Diabetes", "Suffering", "Important", "3.7", "hours", "0.31"),
        # E0007 - multi at-risk
        (
            "E0007",
            "Sleep",
            "Cardiovascular Disease",
            "At Risk",
            "Important",
            "6.6",
            "hours",
            "0.30",
        ),
        ("E0007", "Wellness", "Mental Illness", "At Risk", "Important", "45", "score", "0.25"),
        # E0008 - osteoporosis
        ("E0008", "Movement", "Osteoporosis", "Suffering", "Important", "25", "score", "0.19"),
    ]
    db.add_all(
        [
            HealthRecord(
                employee_id=eid,
                record_date=DEFAULT_RECORD_DATE,
                factor=factor,
                health_condition=condition,
                status=status,
                severity=severity,
                value=Decimal(value),
                unit=unit,
                improvement_rate=Decimal(improv),
            )
            for (eid, factor, condition, status, severity, value, unit, improv) in legacy_records
        ]
    )
    db.commit()


# ----- New tenant employees + records (generated) -----


def _weighted_pick(rng: random.Random, profile: list[tuple]) -> tuple:
    """Pick one row from a tenant profile using its weight column."""
    weights = [row[6] for row in profile]
    return rng.choices(profile, weights=weights, k=1)[0]


def _generate_employee_records(
    rng: random.Random,
    employee_id: str,
    profile: list[tuple],
) -> list[HealthRecord]:
    """Generate 2 or 3 records for one employee, drawn from the tenant
    profile. Avoid duplicate (factor, condition) pairs within one employee.
    """
    n = rng.randint(2, 3)
    chosen: list[tuple] = []
    seen: set[tuple[str, str]] = set()
    attempts = 0
    while len(chosen) < n and attempts < 20:
        attempts += 1
        row = _weighted_pick(rng, profile)
        key = (row[0], row[1])
        if key in seen:
            continue
        seen.add(key)
        chosen.append(row)

    return [
        HealthRecord(
            employee_id=employee_id,
            record_date=DEFAULT_RECORD_DATE,
            factor=row[0],
            health_condition=row[1],
            severity=row[2],
            status=row[3],
            value=Decimal(row[4]),
            unit=row[5],
            improvement_rate=Decimal("0.20"),
        )
        for row in chosen
    ]


def seed_new_tenant_employees_and_records(db: Session) -> None:
    """Generate 30 employees per new tenant, 2-3 records each."""
    rng = random.Random(SEED)

    for spec in NEW_TENANT_SPECS:
        tenant_id = spec["tenant_id"]
        prefix = spec["prefix"]
        profile = spec["profile"]
        count = spec["count"]
        regions = REGIONS_BY_TENANT[tenant_id]
        legacy_tenant_str = LEGACY_TENANT_STRING[tenant_id]

        print(f"Seeding {count} employees for {tenant_id}...")
        employees = []
        all_records = []
        for i in range(1, count + 1):
            employee_id = f"{prefix}{i:03d}"
            region = regions[i % len(regions)]
            employees.append(
                Employee(
                    id=employee_id,
                    region=region,
                    tenant=legacy_tenant_str,
                    tenant_id=tenant_id,
                )
            )
            all_records.extend(_generate_employee_records(rng, employee_id, profile))

        db.add_all(employees)
        db.commit()
        db.add_all(all_records)
        db.commit()


# ----- Products (unchanged) -----


def seed_products(db: Session) -> None:
    print("Seeding products...")

    products_data = [
        # Factor services
        {
            "name": "Sleep Hygiene Coaching Program",
            "description": "8-week program to improve sleep quality through habits and environment.",
            "category": "program",
            "service_type": "factor_service",
            "price": Decimal("299.00"),
            "factors": [("Sleep", Decimal("1.00"))],
            "conditions": [
                ("Cardiovascular Disease", Decimal("0.60")),
                ("Mental Illness", Decimal("0.50")),
            ],
        },
        {
            "name": "Mindfulness & Stress Management App",
            "description": "Daily guided meditation and stress-reduction techniques.",
            "category": "app",
            "service_type": "factor_service",
            "price": Decimal("12.99"),
            "factors": [("Stress", Decimal("1.00")), ("Depression", Decimal("0.70"))],
            "conditions": [
                ("Cardiovascular Disease", Decimal("0.50")),
                ("Mental Illness", Decimal("0.80")),
            ],
        },
        {
            "name": "Nutrition Counseling Service",
            "description": "1-on-1 sessions with registered dietitian.",
            "category": "service",
            "service_type": "factor_service",
            "price": Decimal("150.00"),
            "factors": [("Nutrition", Decimal("1.00")), ("Obesity", Decimal("0.80"))],
            "conditions": [
                ("Type 2 Diabetes", Decimal("0.90")),
                ("Cardiovascular Disease", Decimal("0.70")),
                ("Chronic Kidney Disease", Decimal("0.60")),
            ],
        },
        {
            "name": "Smoking Cessation Program",
            "description": "Evidence-based program to quit smoking with support and tools.",
            "category": "program",
            "service_type": "factor_service",
            "price": Decimal("400.00"),
            "factors": [("Smoke", Decimal("1.00"))],
            "conditions": [
                ("Cardiovascular Disease", Decimal("0.95")),
                ("Cancer", Decimal("0.90")),
            ],
        },
        {
            "name": "Physical Activity Tracker + Coach",
            "description": "Wearable device with virtual fitness coaching.",
            "category": "device",
            "service_type": "factor_service",
            "price": Decimal("249.00"),
            "factors": [("Movement", Decimal("1.00")), ("Obesity", Decimal("0.70"))],
            "conditions": [
                ("Cardiovascular Disease", Decimal("0.70")),
                ("Type 2 Diabetes", Decimal("0.80")),
                ("Osteoporosis", Decimal("0.85")),
            ],
        },
        {
            "name": "Mental Health Therapy Sessions",
            "description": "Licensed therapist sessions, virtual or in-person.",
            "category": "service",
            "service_type": "factor_service",
            "price": Decimal("180.00"),
            "factors": [("Depression", Decimal("1.00")), ("Wellness", Decimal("0.80"))],
            "conditions": [("Mental Illness", Decimal("1.00"))],
        },
        # Condition services
        {
            "name": "Diabetes Management Program",
            "description": "Comprehensive program with glucose monitoring and dietitian.",
            "category": "program",
            "service_type": "condition_service",
            "price": Decimal("599.00"),
            "factors": [("Nutrition", Decimal("0.80")), ("Movement", Decimal("0.70"))],
            "conditions": [("Type 2 Diabetes", Decimal("1.00"))],
        },
        {
            "name": "Cardiac Rehabilitation Program",
            "description": "Supervised exercise and lifestyle program for heart health.",
            "category": "program",
            "service_type": "condition_service",
            "price": Decimal("799.00"),
            "factors": [("Movement", Decimal("0.80")), ("Stress", Decimal("0.60"))],
            "conditions": [("Cardiovascular Disease", Decimal("1.00"))],
        },
        {
            "name": "Renal Health Diet Plan",
            "description": "Specialized diet planning for kidney health.",
            "category": "service",
            "service_type": "condition_service",
            "price": Decimal("250.00"),
            "factors": [("Nutrition", Decimal("0.90"))],
            "conditions": [("Chronic Kidney Disease", Decimal("1.00"))],
        },
        {
            "name": "Cancer Patient Support Network",
            "description": "Counseling, peer support, and lifestyle guidance during treatment.",
            "category": "service",
            "service_type": "condition_service",
            "price": Decimal("0.00"),
            "factors": [("Wellness", Decimal("0.70")), ("Depression", Decimal("0.60"))],
            "conditions": [("Cancer", Decimal("1.00"))],
        },
        {
            "name": "Bone Health Program",
            "description": "Strength training and calcium/vitamin D supplementation guidance.",
            "category": "program",
            "service_type": "condition_service",
            "price": Decimal("349.00"),
            "factors": [("Movement", Decimal("0.85")), ("Nutrition", Decimal("0.70"))],
            "conditions": [("Osteoporosis", Decimal("1.00"))],
        },
        {
            "name": "Mental Illness Care Coordination",
            "description": "Integrated psychiatric and therapy services.",
            "category": "service",
            "service_type": "condition_service",
            "price": Decimal("450.00"),
            "factors": [("Depression", Decimal("0.90")), ("Stress", Decimal("0.70"))],
            "conditions": [("Mental Illness", Decimal("1.00"))],
        },
    ]

    for data in products_data:
        product = Product(
            name=data["name"],
            description=data["description"],
            category=data["category"],
            service_type=data["service_type"],
            price=data["price"],
        )
        db.add(product)
        db.flush()

        for factor_name, score in data["factors"]:
            db.add(
                ProductFactor(
                    product_id=product.id,
                    factor=factor_name,
                    relevance_score=score,
                )
            )
        for cond_name, score in data["conditions"]:
            db.add(
                ProductCondition(
                    product_id=product.id,
                    health_condition=cond_name,
                    relevance_score=score,
                )
            )

    db.commit()


# ----- Main -----


def main() -> None:
    db = SessionLocal()
    try:
        clear_all_data(db)
        seed_tenants(db)
        seed_original_employees_and_records(db)
        seed_new_tenant_employees_and_records(db)
        seed_products(db)

        print("\nSeed complete.")
        print(f"  Tenants: {db.query(Tenant).count()}")
        print(f"  Employees total: {db.query(Employee).count()}")
        for tenant in db.query(Tenant).order_by(Tenant.id).all():
            count = db.query(Employee).filter(Employee.tenant_id == tenant.id).count()
            print(f"    {tenant.id} ({tenant.name}): {count}")
        print(f"  Health records: {db.query(HealthRecord).count()}")
        print(f"  Products: {db.query(Product).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
