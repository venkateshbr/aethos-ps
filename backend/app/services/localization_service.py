"""Launch-market localization profiles.

This module is the backend source of truth for the five launch markets. It is
intentionally independent of Stripe, signup, and tax-rate settings so those
surfaces can reuse the same country, currency, locale, timezone, and tax labels.
"""

from __future__ import annotations

from typing import Final

from app.models.localization import MarketProfileResponse, TaxRateTemplate


def _tax_template(
    code: str,
    name: str,
    rate: str,
    *,
    is_default: bool = False,
) -> TaxRateTemplate:
    return TaxRateTemplate(code=code, name=name, rate=rate, is_default=is_default)


_MARKET_PROFILES_BY_COUNTRY: Final[dict[str, MarketProfileResponse]] = {
    "US": MarketProfileResponse(
        country="US",
        market="US",
        country_name="United States",
        base_currency="USD",
        locale="en-US",
        timezone="America/New_York",
        tax_label="Sales tax",
        tax_registration_label="EIN",
        invoice_tax_label="Sales tax",
        tax_authority_label="IRS and state tax agencies",
        tax_collection_model="jurisdictional_sales_tax",
        default_tax_rate_code=None,
        reporting_periods=["monthly", "quarterly", "annual"],
        fiscal_year_label="Calendar year default",
        tax_rate_templates=[
            _tax_template("US-EXEMPT", "US Tax Exempt / No Tax", "0.00"),
        ],
    ),
    "GB": MarketProfileResponse(
        country="GB",
        market="UK",
        country_name="United Kingdom",
        base_currency="GBP",
        locale="en-GB",
        timezone="Europe/London",
        tax_label="VAT",
        tax_registration_label="VAT registration number",
        invoice_tax_label="VAT",
        tax_authority_label="HMRC",
        tax_collection_model="vat",
        default_tax_rate_code="VAT-20",
        reporting_periods=["monthly", "quarterly", "annual"],
        fiscal_year_label="Company year-end default",
        tax_rate_templates=[
            _tax_template("VAT-20", "UK VAT Standard Rate (20%)", "20.00", is_default=True),
            _tax_template("VAT-5", "UK VAT Reduced Rate (5%)", "5.00"),
            _tax_template("VAT-0", "UK VAT Zero Rate (0%)", "0.00"),
        ],
    ),
    "SG": MarketProfileResponse(
        country="SG",
        market="SG",
        country_name="Singapore",
        base_currency="SGD",
        locale="en-SG",
        timezone="Asia/Singapore",
        tax_label="GST",
        tax_registration_label="GST registration number",
        invoice_tax_label="GST",
        tax_authority_label="IRAS",
        tax_collection_model="gst",
        default_tax_rate_code="GST-9",
        reporting_periods=["monthly", "quarterly", "annual"],
        fiscal_year_label="Company financial year default",
        tax_rate_templates=[
            _tax_template("GST-9", "Singapore GST (9%)", "9.00", is_default=True),
            _tax_template("GST-0", "Singapore GST Zero-Rated (0%)", "0.00"),
        ],
    ),
    "IN": MarketProfileResponse(
        country="IN",
        market="IN",
        country_name="India",
        base_currency="INR",
        locale="en-IN",
        timezone="Asia/Kolkata",
        tax_label="GST",
        tax_registration_label="GSTIN",
        invoice_tax_label="GST",
        tax_authority_label="GSTN",
        tax_collection_model="gst_cgst_sgst_igst",
        default_tax_rate_code="GST-IN-18",
        reporting_periods=["monthly", "quarterly", "annual"],
        fiscal_year_label="April-March financial year default",
        tax_rate_templates=[
            _tax_template("GST-IN-0", "India GST 0%", "0.00"),
            _tax_template("GST-IN-5", "India GST 5%", "5.00"),
            _tax_template("GST-IN-12", "India GST 12%", "12.00"),
            _tax_template("GST-IN-18", "India GST 18%", "18.00", is_default=True),
            _tax_template("GST-IN-28", "India GST 28%", "28.00"),
        ],
    ),
    "AU": MarketProfileResponse(
        country="AU",
        market="AU",
        country_name="Australia",
        base_currency="AUD",
        locale="en-AU",
        timezone="Australia/Sydney",
        tax_label="GST",
        tax_registration_label="ABN",
        invoice_tax_label="GST",
        tax_authority_label="Australian Taxation Office",
        tax_collection_model="gst",
        default_tax_rate_code="GST-AU-10",
        reporting_periods=["monthly", "quarterly", "annual"],
        fiscal_year_label="July-June financial year default",
        tax_rate_templates=[
            _tax_template("GST-AU-10", "Australia GST (10%)", "10.00", is_default=True),
            _tax_template("GST-AU-0", "Australia GST Exports (0%)", "0.00"),
        ],
    ),
}

_MARKET_TO_COUNTRY: Final[dict[str, str]] = {
    profile.market: country for country, profile in _MARKET_PROFILES_BY_COUNTRY.items()
}
_MARKET_TO_COUNTRY["UK"] = "GB"


def normalize_country_or_market(value: str | None) -> str | None:
    """Normalize a product market or ISO country code to a country code."""
    if value is None:
        return None
    normalized = value.strip().upper()
    if not normalized:
        return None
    return _MARKET_TO_COUNTRY.get(normalized, normalized)


def country_to_market(country: str | None) -> str | None:
    """Return product-facing market code for a country code."""
    normalized = normalize_country_or_market(country)
    if normalized is None:
        return None
    profile = _MARKET_PROFILES_BY_COUNTRY.get(normalized)
    return profile.market if profile else normalized


def market_to_country(market: str | None) -> str | None:
    """Return ISO country code for a product-facing market code."""
    return normalize_country_or_market(market)


def country_to_currency(country: str) -> str:
    """Return the launch-market base currency, defaulting to USD."""
    profile = get_market_profile(country)
    return profile.base_currency if profile else "USD"


def get_market_profile(country_or_market: str | None) -> MarketProfileResponse | None:
    """Return a defensive copy of a market profile, or None if unsupported."""
    normalized = normalize_country_or_market(country_or_market)
    if normalized is None:
        return None
    profile = _MARKET_PROFILES_BY_COUNTRY.get(normalized)
    return profile.model_copy(deep=True) if profile else None


def list_market_profiles() -> list[MarketProfileResponse]:
    """Return all launch-market profiles in signup display order."""
    return [
        _MARKET_PROFILES_BY_COUNTRY[country].model_copy(deep=True)
        for country in ("US", "GB", "SG", "IN", "AU")
    ]
