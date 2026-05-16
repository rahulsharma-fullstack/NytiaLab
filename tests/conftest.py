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

    db_session.add_all(
        [
            Employee(id="E0001", region="Central East", tenant="NYTIA"),
            Employee(id="E0002", region="North West", tenant="NYTIA"),
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
