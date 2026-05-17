"""Integration tests for the /tenants endpoints.

Exercises the full HTTP stack against an in-memory SQLite database seeded
by the `seeded_org_db` fixture (see `tests/conftest.py`).

Covered:
- GET /tenants returns every tenant (here: 3 from the org fixture).
- GET /tenants/{id} works and 404s with the standard {error, detail} shape.
- GET /tenants/{id}/profile has correct math (counts, percentages,
  pressure sort order) and 404s on unknown tenants.
- GET /tenants/{id}/recommendations is ranked correctly, includes the
  population-aware reason strings, contains tenant_name (router
  enrichment), and 404s on unknown tenants.
- top_n bounds are validated.
- Empty workforce returns an empty recommendations list with 200.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# ---------------- /tenants ----------------


def test_list_tenants_returns_all(client: TestClient, seeded_org_db: Session) -> None:
    response = client.get("/tenants")
    assert response.status_code == 200
    body = response.json()
    ids = {t["id"] for t in body}
    assert ids == {"T_TEST_IBM", "T_TEST_MS", "T_TEST_EMPTY"}


def test_get_tenant_by_id_returns_one(client: TestClient, seeded_org_db: Session) -> None:
    response = client.get("/tenants/T_TEST_IBM")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "T_TEST_IBM"
    assert body["name"] == "Test IBM"


def test_get_tenant_missing_returns_404_with_standard_shape(
    client: TestClient, seeded_org_db: Session
) -> None:
    response = client.get("/tenants/T_NOPE")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "tenant_not_found"
    assert "T_NOPE" in body["detail"]


# ---------------- /tenants/{id}/profile ----------------


def test_profile_math_for_mental_health_heavy_tenant(
    client: TestClient, seeded_org_db: Session
) -> None:
    response = client.get("/tenants/T_TEST_IBM/profile")
    assert response.status_code == 200
    body = response.json()

    assert body["tenant_id"] == "T_TEST_IBM"
    assert body["tenant_name"] == "Test IBM"
    assert body["total_employees"] == 4

    # Conditions: only Mental Illness should appear, with 3 Suffering + 1 At Risk.
    assert len(body["conditions"]) == 1
    cond = body["conditions"][0]
    assert cond["name"] == "Mental Illness"
    assert cond["suffering_count"] == 3
    assert cond["at_risk_count"] == 1
    assert cond["total_affected"] == 4
    assert cond["percent_affected"] == 100.0
    assert cond["pressure_score"] > 0

    # Factors: Stress (2), Sleep (1), Depression (1).
    factor_names = {f["name"] for f in body["factors"]}
    assert factor_names == {"Stress", "Sleep", "Depression"}
    # Stress appears in 2 employees, should have the highest pressure of the three.
    stress = next(f for f in body["factors"] if f["name"] == "Stress")
    assert stress["total_affected"] == 2


def test_profile_for_empty_tenant_returns_zero_employees_and_empty_lists(
    client: TestClient, seeded_org_db: Session
) -> None:
    response = client.get("/tenants/T_TEST_EMPTY/profile")
    assert response.status_code == 200
    body = response.json()
    assert body["total_employees"] == 0
    assert body["conditions"] == []
    assert body["factors"] == []


def test_profile_unknown_tenant_returns_404(client: TestClient, seeded_org_db: Session) -> None:
    response = client.get("/tenants/T_NOPE/profile")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "tenant_not_found"


# ---------------- /tenants/{id}/recommendations ----------------


def test_recommendations_for_mental_health_heavy_tenant_top_is_therapy(
    client: TestClient, seeded_org_db: Session
) -> None:
    response = client.get("/tenants/T_TEST_IBM/recommendations")
    assert response.status_code == 200
    body = response.json()

    # tenant_name comes from the router enrichment (TenantService lookup).
    assert body["tenant_id"] == "T_TEST_IBM"
    assert body["tenant_name"] == "Test IBM"
    assert body["total_employees"] == 4
    assert body["algorithm_version"] == "org-rules-v1"

    recs = body["recommendations"]
    assert len(recs) >= 1
    top = recs[0]
    # Mental Health Therapy targets Mental Illness, which 100% of the
    # workforce has. It must rank #1.
    assert top["product_name"] == "Mental Health Therapy"
    assert top["score"] > 0
    # Reasons must include the population reach for Mental Illness.
    joined = " ".join(top["reasons"])
    assert "Mental Illness" in joined
    assert "4 of your 4 employees" in joined
    assert "100.0%" in joined

    # Bone Health Program targets Osteoporosis which this workforce does
    # not have, so it must NOT be in the result list (zero-score exclusion).
    names = [r["product_name"] for r in recs]
    assert "Bone Health Program" not in names


def test_recommendations_for_diabetes_heavy_tenant_top_is_diabetes_program(
    client: TestClient, seeded_org_db: Session
) -> None:
    response = client.get("/tenants/T_TEST_MS/recommendations")
    assert response.status_code == 200
    body = response.json()
    assert body["tenant_name"] == "Test Microsoft"
    top = body["recommendations"][0]
    assert top["product_name"] == "Diabetes Management Program"
    joined = " ".join(top["reasons"])
    assert "Type 2 Diabetes" in joined
    assert "2 of your 2 employees" in joined


def test_recommendations_respects_top_n(client: TestClient, seeded_org_db: Session) -> None:
    response = client.get("/tenants/T_TEST_IBM/recommendations", params={"top_n": 1})
    assert response.status_code == 200
    body = response.json()
    assert len(body["recommendations"]) == 1


def test_recommendations_top_n_bounds_rejected(client: TestClient, seeded_org_db: Session) -> None:
    # too small
    response = client.get("/tenants/T_TEST_IBM/recommendations", params={"top_n": 0})
    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"

    # too large
    response = client.get("/tenants/T_TEST_IBM/recommendations", params={"top_n": 51})
    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


def test_recommendations_for_empty_tenant_returns_empty_list(
    client: TestClient, seeded_org_db: Session
) -> None:
    response = client.get("/tenants/T_TEST_EMPTY/recommendations")
    assert response.status_code == 200
    body = response.json()
    assert body["tenant_name"] == "Test Empty"
    assert body["total_employees"] == 0
    assert body["recommendations"] == []


def test_recommendations_unknown_tenant_returns_404(
    client: TestClient, seeded_org_db: Session
) -> None:
    response = client.get("/tenants/T_NOPE/recommendations")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "tenant_not_found"
