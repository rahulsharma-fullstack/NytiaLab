"""Shared pytest fixtures for endpoint tests.

We use an in-memory SQLite database so tests are fast, isolated, and do not
need a running Postgres. The FastAPI `get_db` dependency is overridden to
yield sessions bound to the test engine.
"""

from collections.abc import Generator
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import (
    Employee,
    HealthRecord,
    Product,
    ProductCondition,
    ProductFactor,
    Tenant,
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """A fresh in-memory SQLite database with schema created.

    Each test gets its own engine + connection, so tests are fully isolated.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient with `get_db` overridden to use the in-memory session."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def seeded_db(db_session: Session) -> Session:
    """A db_session with a small, deterministic dataset for endpoint tests."""
    today = date(2026, 1, 3)

    # Tenant row required because employees.tenant_id is NOT NULL with an FK
    # to tenants.id. Pure test plumbing; no test assertion checks this.
    db_session.add(Tenant(id="T_NYTIA_DEMO", name="Nytia Demo"))
    db_session.flush()

    db_session.add_all(
        [
            Employee(
                id="E0001",
                region="Central East",
                tenant="NYTIA",
                tenant_id="T_NYTIA_DEMO",
            ),
            Employee(
                id="E0002",
                region="North West",
                tenant="NYTIA",
                tenant_id="T_NYTIA_DEMO",
            ),
        ]
    )

    db_session.add_all(
        [
            HealthRecord(
                employee_id="E0001",
                record_date=today,
                factor="Nutrition",
                health_condition="Type 2 Diabetes",
                status="Suffering",
                severity="Very Important",
                value=Decimal("54"),
                unit="score",
                improvement_rate=Decimal("0.32"),
            ),
            HealthRecord(
                employee_id="E0002",
                record_date=today,
                factor="Movement",
                health_condition="Osteoporosis",
                status="At Risk",
                severity="Important",
                value=Decimal("25"),
                unit="score",
                improvement_rate=Decimal("0.20"),
            ),
        ]
    )

    diabetes = Product(
        name="Diabetes Management Program",
        description="Glucose monitoring + dietitian.",
        category="program",
        service_type="condition_service",
        price=Decimal("599.00"),
        is_active=True,
    )
    nutrition = Product(
        name="Nutrition Counseling Service",
        description="1-on-1 sessions with registered dietitian.",
        category="service",
        service_type="factor_service",
        price=Decimal("150.00"),
        is_active=True,
    )
    bone = Product(
        name="Bone Health Program",
        description="Strength training and calcium guidance.",
        category="program",
        service_type="condition_service",
        price=Decimal("349.00"),
        is_active=True,
    )

    db_session.add_all([diabetes, nutrition, bone])
    db_session.flush()

    db_session.add_all(
        [
            ProductCondition(
                product_id=diabetes.id,
                health_condition="Type 2 Diabetes",
                relevance_score=Decimal("1.00"),
            ),
            ProductFactor(
                product_id=diabetes.id,
                factor="Nutrition",
                relevance_score=Decimal("0.80"),
            ),
            ProductFactor(
                product_id=nutrition.id,
                factor="Nutrition",
                relevance_score=Decimal("1.00"),
            ),
            ProductCondition(
                product_id=nutrition.id,
                health_condition="Type 2 Diabetes",
                relevance_score=Decimal("0.90"),
            ),
            ProductCondition(
                product_id=bone.id,
                health_condition="Osteoporosis",
                relevance_score=Decimal("1.00"),
            ),
            ProductFactor(
                product_id=bone.id,
                factor="Movement",
                relevance_score=Decimal("0.85"),
            ),
        ]
    )

    db_session.commit()
    return db_session


@pytest.fixture
def seeded_org_db(db_session: Session) -> Session:
    """A richer dataset designed for the org-level endpoint tests.

    Three tenants:
      T_TEST_IBM   : 4 employees, mental-health-heavy
      T_TEST_MS    : 2 employees, diabetes-heavy
      T_TEST_EMPTY : 0 employees (used to test empty-workforce path)

    Three products that cover the conditions/factors above plus one that
    targets neither, so we can also test zero-score exclusion.
    """
    today = date(2026, 1, 3)

    db_session.add_all(
        [
            Tenant(id="T_TEST_IBM", name="Test IBM"),
            Tenant(id="T_TEST_MS", name="Test Microsoft"),
            Tenant(id="T_TEST_EMPTY", name="Test Empty"),
        ]
    )
    db_session.flush()

    # IBM-flavoured: mental-health-heavy population
    ibm_employees = [
        ("E_T1_1", "Stress", "Mental Illness", "Suffering", "Very Important"),
        ("E_T1_2", "Sleep", "Mental Illness", "Suffering", "Very Important"),
        ("E_T1_3", "Depression", "Mental Illness", "Suffering", "Very Important"),
        ("E_T1_4", "Stress", "Mental Illness", "At Risk", "Important"),
    ]
    for emp_id, factor, condition, status, severity in ibm_employees:
        db_session.add(
            Employee(
                id=emp_id,
                region="Toronto",
                tenant="IBM",
                tenant_id="T_TEST_IBM",
            )
        )
        db_session.flush()
        db_session.add(
            HealthRecord(
                employee_id=emp_id,
                record_date=today,
                factor=factor,
                health_condition=condition,
                status=status,
                severity=severity,
                value=Decimal("50"),
                unit="score",
                improvement_rate=Decimal("0.20"),
            )
        )

    # Microsoft-flavoured: diabetes-heavy population
    ms_employees = [
        ("E_T2_1", "Nutrition", "Type 2 Diabetes", "Suffering", "Important"),
        ("E_T2_2", "Obesity", "Type 2 Diabetes", "Suffering", "Important"),
    ]
    for emp_id, factor, condition, status, severity in ms_employees:
        db_session.add(
            Employee(
                id=emp_id,
                region="Vancouver",
                tenant="Microsoft",
                tenant_id="T_TEST_MS",
            )
        )
        db_session.flush()
        db_session.add(
            HealthRecord(
                employee_id=emp_id,
                record_date=today,
                factor=factor,
                health_condition=condition,
                status=status,
                severity=severity,
                value=Decimal("70"),
                unit="score",
                improvement_rate=Decimal("0.20"),
            )
        )

    # Products
    mh_therapy = Product(
        name="Mental Health Therapy",
        description="Therapy sessions.",
        category="service",
        service_type="factor_service",
        price=Decimal("180.00"),
        is_active=True,
    )
    diabetes = Product(
        name="Diabetes Management Program",
        description="Glucose monitoring + diet.",
        category="program",
        service_type="condition_service",
        price=Decimal("599.00"),
        is_active=True,
    )
    bone = Product(
        name="Bone Health Program",
        description="Strength + calcium.",
        category="program",
        service_type="condition_service",
        price=Decimal("349.00"),
        is_active=True,
    )
    db_session.add_all([mh_therapy, diabetes, bone])
    db_session.flush()

    db_session.add_all(
        [
            ProductCondition(
                product_id=mh_therapy.id,
                health_condition="Mental Illness",
                relevance_score=Decimal("1.00"),
            ),
            ProductFactor(
                product_id=mh_therapy.id,
                factor="Depression",
                relevance_score=Decimal("1.00"),
            ),
            ProductCondition(
                product_id=diabetes.id,
                health_condition="Type 2 Diabetes",
                relevance_score=Decimal("1.00"),
            ),
            ProductFactor(
                product_id=diabetes.id,
                factor="Nutrition",
                relevance_score=Decimal("0.80"),
            ),
            ProductCondition(
                product_id=bone.id,
                health_condition="Osteoporosis",
                relevance_score=Decimal("1.00"),
            ),
        ]
    )

    db_session.commit()
    return db_session
