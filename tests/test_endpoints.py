"""Integration tests for the main API endpoints.

These run against an in-memory SQLite database seeded with a small fixture.
They exercise the full HTTP stack: routers, services, repositories, schemas.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# ----------------- Employees -----------------


def test_list_employees(client: TestClient, seeded_db: Session) -> None:
    response = client.get("/employees")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    ids = {e["id"] for e in body}
    assert ids == {"E0001", "E0002"}


def test_get_employee_by_id(client: TestClient, seeded_db: Session) -> None:
    response = client.get("/employees/E0001")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "E0001"
    assert body["region"] == "Central East"


def test_get_employee_missing_returns_404(client: TestClient, seeded_db: Session) -> None:
    response = client.get("/employees/E9999")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "employee_not_found"


def test_get_health_records_for_employee(client: TestClient, seeded_db: Session) -> None:
    response = client.get("/employees/E0001/health-records")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["factor"] == "Nutrition"
    assert body[0]["health_condition"] == "Type 2 Diabetes"
    assert body[0]["status"] == "Suffering"
    assert body[0]["severity"] == "Very Important"


# ----------------- Products -----------------


def test_list_products(client: TestClient, seeded_db: Session) -> None:
    response = client.get("/products")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3


def test_filter_products_by_condition(client: TestClient, seeded_db: Session) -> None:
    response = client.get("/products", params={"condition": "Type 2 Diabetes"})
    assert response.status_code == 200
    body = response.json()
    names = {p["name"] for p in body}
    assert "Diabetes Management Program" in names
    assert "Nutrition Counseling Service" in names
    assert "Bone Health Program" not in names


def test_filter_products_by_service_type(client: TestClient, seeded_db: Session) -> None:
    response = client.get("/products", params={"service_type": "factor_service"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Nutrition Counseling Service"


# ----------------- Recommendations -----------------


def test_recommend_for_employee_returns_ranked_results(
    client: TestClient, seeded_db: Session
) -> None:
    response = client.get("/recommend/E0001")
    assert response.status_code == 200
    body = response.json()

    assert body["employee_id"] == "E0001"
    assert body["algorithm_version"] == "rules-v1"
    assert len(body["recommendations"]) >= 2

    top = body["recommendations"][0]
    assert top["score"] > 0
    assert len(top["reasons"]) >= 1

    # The diabetes-relevant products should both appear, the osteoporosis-only
    # one should be excluded.
    names = [r["name"] for r in body["recommendations"]]
    assert "Diabetes Management Program" in names
    assert "Nutrition Counseling Service" in names
    assert "Bone Health Program" not in names


def test_recommend_respects_top_n(client: TestClient, seeded_db: Session) -> None:
    response = client.get("/recommend/E0001", params={"top_n": 1})
    assert response.status_code == 200
    body = response.json()
    assert len(body["recommendations"]) == 1


def test_recommend_for_missing_employee_returns_404(client: TestClient, seeded_db: Session) -> None:
    response = client.get("/recommend/E9999")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "employee_not_found"


def test_recommend_validates_top_n_bounds(client: TestClient, seeded_db: Session) -> None:
    response = client.get("/recommend/E0001", params={"top_n": 0})
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
