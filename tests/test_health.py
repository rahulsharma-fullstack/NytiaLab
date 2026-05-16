"""Tests for the /health and / root endpoints."""

from fastapi.testclient import TestClient


def test_root_endpoint_returns_metadata(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Nytia Recommender API"
    assert "docs" in body


def test_health_endpoint_returns_healthy(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "version" in body


def test_response_includes_request_id_header(client: TestClient) -> None:
    response = client.get("/health")
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) >= 8
