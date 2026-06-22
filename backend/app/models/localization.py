"""Pydantic schemas for launch-market localization metadata."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TaxRateTemplate(BaseModel):
    """System tax-rate template exposed as market reference data."""

    code: str
    name: str
    rate: str = Field(description="Percentage rate, for example '20.00'")
    is_default: bool = False


class MarketProfileResponse(BaseModel):
    """Localization profile for a supported launch market."""

    country: str = Field(description="ISO 3166-1 alpha-2 country code")
    market: str = Field(description="Product-facing market code")
    country_name: str
    base_currency: str = Field(description="ISO 4217 base currency")
    locale: str
    timezone: str
    tax_label: str
    tax_registration_label: str
    invoice_tax_label: str
    tax_authority_label: str
    tax_collection_model: str
    default_tax_rate_code: str | None
    reporting_periods: list[str]
    fiscal_year_label: str
    tax_rate_templates: list[TaxRateTemplate]
