"""Localization API contract tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.unit


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_list_market_profiles_is_public_reference_data(client: TestClient) -> None:
    response = client.get("/api/v1/localization/market-profiles")

    assert response.status_code == 200, response.text
    body = response.json()
    assert [profile["country"] for profile in body] == ["US", "GB", "SG", "IN", "AU"]
    assert body[1]["market"] == "UK"
    assert body[1]["base_currency"] == "GBP"
    assert body[3]["tax_registration_label"] == "GSTIN"
    assert body[3]["default_tax_rate_code"] == "GST-IN-18"


def test_get_market_profile_accepts_country_or_market(client: TestClient) -> None:
    by_market = client.get("/api/v1/localization/market-profiles/UK")
    by_country = client.get("/api/v1/localization/market-profiles/gb")

    assert by_market.status_code == 200, by_market.text
    assert by_country.status_code == 200, by_country.text
    assert by_market.json() == by_country.json()
    assert by_market.json()["country"] == "GB"
    assert by_market.json()["tax_label"] == "VAT"


def test_get_market_profile_returns_404_for_unsupported_market(client: TestClient) -> None:
    response = client.get("/api/v1/localization/market-profiles/DE")

    assert response.status_code == 404
    assert response.json()["detail"] == "Market profile not found"
