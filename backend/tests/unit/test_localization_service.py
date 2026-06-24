"""Unit tests for launch-market localization profiles."""

from __future__ import annotations

import pytest

from app.services.localization_service import (
    country_to_currency,
    country_to_market,
    get_market_profile,
    list_market_profiles,
    market_to_country,
)

pytestmark = pytest.mark.unit


def test_market_profiles_cover_5_launch_markets() -> None:
    profiles = list_market_profiles()

    assert [profile.country for profile in profiles] == ["US", "GB", "SG", "IN", "AU"]
    assert [profile.market for profile in profiles] == ["US", "UK", "SG", "IN", "AU"]
    assert {profile.base_currency for profile in profiles} == {
        "USD",
        "GBP",
        "SGD",
        "INR",
        "AUD",
    }


def test_market_profile_contains_tax_reporting_defaults() -> None:
    india = get_market_profile("IN")

    assert india is not None
    assert india.locale == "en-IN"
    assert india.timezone == "Asia/Kolkata"
    assert india.tax_registration_label == "GSTIN"
    assert india.default_tax_rate_code == "GST-IN-18"
    assert {template.rate for template in india.tax_rate_templates} == {
        "0.00",
        "5.00",
        "12.00",
        "18.00",
        "28.00",
    }


def test_uk_market_normalizes_to_gb_country() -> None:
    assert market_to_country("UK") == "GB"
    assert market_to_country("gb") == "GB"
    assert country_to_market("GB") == "UK"
    assert country_to_market("uk") == "UK"

    profile = get_market_profile("UK")
    assert profile is not None
    assert profile.country == "GB"
    assert profile.market == "UK"
    assert profile.base_currency == "GBP"


def test_country_to_currency_reuses_profiles_with_usd_fallback() -> None:
    assert country_to_currency("US") == "USD"
    assert country_to_currency("gb") == "GBP"
    assert country_to_currency("SG") == "SGD"
    assert country_to_currency("IN") == "INR"
    assert country_to_currency("AU") == "AUD"
    assert country_to_currency("DE") == "USD"


def test_market_profiles_are_defensive_copies() -> None:
    profile = get_market_profile("AU")
    assert profile is not None
    profile.tax_rate_templates.clear()

    fresh_profile = get_market_profile("AU")
    assert fresh_profile is not None
    assert [template.code for template in fresh_profile.tax_rate_templates] == [
        "GST-AU-10",
        "GST-AU-0",
    ]
