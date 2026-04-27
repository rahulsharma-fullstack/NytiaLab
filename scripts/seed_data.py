"""Seed the database with sample data for development.

Run this from the project root:
    uv run python scripts/seed_data.py

This deletes existing data and reinserts a fresh sample.
Safe to run multiple times.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Employee,
    HealthRecord,
    Product,
    ProductCondition,
    ProductFactor,
)


def clear_all_data(db: Session) -> None:
    """Delete all rows from all tables. Order matters for foreign keys."""
    print("Clearing existing data...")
    db.query(ProductCondition).delete()
    db.query(ProductFactor).delete()
    db.query(HealthRecord).delete()
    db.query(Product).delete()
    db.query(Employee).delete()
    db.commit()


def seed_employees(db: Session) -> None:
    """Insert sample employees across different Ontario regions."""
    print("Seeding employees...")
    employees = [
        Employee(id="E0001", region="Waterloo Wellington", tenant="NYTIA"),
        Employee(id="E0002", region="Central East", tenant="NYTIA"),
        Employee(id="E0003", region="Central West", tenant="NYTIA"),
        Employee(id="E0004", region="South East", tenant="NYTIA"),
        Employee(id="E0005", region="North Simcoe", tenant="NYTIA"),
        Employee(id="E0006", region="Erie St. Clair", tenant="NYTIA"),
        Employee(id="E0007", region="Waterloo Wellington", tenant="NYTIA"),
        Employee(id="E0008", region="North West", tenant="NYTIA"),
    ]
    db.add_all(employees)
    db.commit()


def seed_health_records(db: Session) -> None:
    """Insert sample health records covering different combinations."""
    print("Seeding health records...")
    today = date(2026, 1, 3)

    records = [
        # E0001 - Sleep issues, suffering, at risk for CVD
        HealthRecord(
            employee_id="E0001", record_date=today,
            factor="Sleep", health_condition="Cardiovascular Disease",
            status="Suffering", severity="Very Important",
            value=Decimal("5.7"), unit="hours",
            improvement_rate=Decimal("0.25"),
        ),
        HealthRecord(
            employee_id="E0001", record_date=today,
            factor="Stress", health_condition="Cardiovascular Disease",
            status="Suffering", severity="Important",
            value=Decimal("69"), unit="score",
            improvement_rate=Decimal("0.23"),
        ),

        # E0002 - Multiple conditions
        HealthRecord(
            employee_id="E0002", record_date=today,
            factor="Depression", health_condition="Mental Illness",
            status="Suffering", severity="Very Important",
            value=Decimal("49"), unit="score",
            improvement_rate=Decimal("0.20"),
        ),
        HealthRecord(
            employee_id="E0002", record_date=today,
            factor="Smoke", health_condition="Cardiovascular Disease",
            status="At Risk", severity="Very Important",
            value=Decimal("99"), unit="score",
            improvement_rate=Decimal("0.17"),
        ),
        HealthRecord(
            employee_id="E0002", record_date=today,
            factor="Nutrition", health_condition="Type 2 Diabetes",
            status="Suffering", severity="Important",
            value=Decimal("54"), unit="score",
            improvement_rate=Decimal("0.32"),
        ),

        # E0003 - Mostly at risk (preventive case)
        HealthRecord(
            employee_id="E0003", record_date=today,
            factor="Nutrition", health_condition="Chronic Kidney Disease",
            status="At Risk", severity="Important",
            value=Decimal("76"), unit="score",
            improvement_rate=Decimal("0.28"),
        ),

        # E0004 - High severity, suffering
        HealthRecord(
            employee_id="E0004", record_date=today,
            factor="Depression", health_condition="Mental Illness",
            status="Suffering", severity="Very Important",
            value=Decimal("86"), unit="score",
            improvement_rate=Decimal("0.21"),
        ),

        # E0005 - Cancer-related
        HealthRecord(
            employee_id="E0005", record_date=today,
            factor="Obesity", health_condition="Cancer",
            status="Suffering", severity="Very Important",
            value=Decimal("60"), unit="score",
            improvement_rate=Decimal("0.18"),
        ),

        # E0006 - Diabetes
        HealthRecord(
            employee_id="E0006", record_date=today,
            factor="Movement", health_condition="Type 2 Diabetes",
            status="Suffering", severity="Important",
            value=Decimal("3.7"), unit="hours",
            improvement_rate=Decimal("0.31"),
        ),

        # E0007 - Multiple factors, at risk
        HealthRecord(
            employee_id="E0007", record_date=today,
            factor="Sleep", health_condition="Cardiovascular Disease",
            status="At Risk", severity="Important",
            value=Decimal("6.6"), unit="hours",
            improvement_rate=Decimal("0.30"),
        ),
        HealthRecord(
            employee_id="E0007", record_date=today,
            factor="Wellness", health_condition="Mental Illness",
            status="At Risk", severity="Important",
            value=Decimal("45"), unit="score",
            improvement_rate=Decimal("0.25"),
        ),

        # E0008 - Osteoporosis case
        HealthRecord(
            employee_id="E0008", record_date=today,
            factor="Movement", health_condition="Osteoporosis",
            status="Suffering", severity="Important",
            value=Decimal("25"), unit="score",
            improvement_rate=Decimal("0.19"),
        ),
    ]
    db.add_all(records)
    db.commit()


def seed_products(db: Session) -> None:
    """Insert sample wellness services with condition/factor tags."""
    print("Seeding products...")

    products_data = [
        # Factor services (preventive)
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

        # Condition services (treatment)
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
        db.flush()  # Get the auto-generated ID

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


def main() -> None:
    """Run the full seed."""
    db = SessionLocal()
    try:
        clear_all_data(db)
        seed_employees(db)
        seed_health_records(db)
        seed_products(db)
        print("\n✓ Seed complete.")
        print(f"  Employees: {db.query(Employee).count()}")
        print(f"  Health records: {db.query(HealthRecord).count()}")
        print(f"  Products: {db.query(Product).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()