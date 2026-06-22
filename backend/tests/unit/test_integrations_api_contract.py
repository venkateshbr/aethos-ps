"""Integration catalog API contract tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.unit


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_integration_catalog_returns_public_roadmap(client: TestClient) -> None:
    response = client.get("/api/v1/integrations/catalog")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= 8
    keys = {item["key"] for item in body["integrations"]}
    assert {"stripe-connect", "bank-feeds", "document-storage"} <= keys


def test_integration_catalog_filters_status(client: TestClient) -> None:
    response = client.get("/api/v1/integrations/catalog?status=available")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 2
    assert {item["status"] for item in body["integrations"]} == {"available"}


def test_integration_catalog_rejects_unknown_status(client: TestClient) -> None:
    response = client.get("/api/v1/integrations/catalog?status=connected")

    assert response.status_code == 422
