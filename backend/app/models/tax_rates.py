"""Pydantic schemas for tenant tax-rate settings."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, field_validator


class TaxRateResponse(BaseModel):
    """Tax rate shape consumed by the Angular settings panel."""

    id: str
    name: str
    rate: str
    market: str | None = None
    is_system: bool
    is_active: bool


class TaxRateCreate(BaseModel):
    """Create a tenant-owned tax rate.

    ``rate`` is supplied as a percentage string, for example ``"8.25"``.
    The database stores rates as fractions, for example ``0.0825``.
    """

    name: str
    rate: Decimal
    market: str | None = None
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required")
        return cleaned

    @field_validator("rate")
    @classmethod
    def validate_rate(cls, value: Decimal) -> Decimal:
        if value < 0 or value > 100:
            raise ValueError("Rate must be between 0 and 100")
        return value


class TaxRateUpdate(BaseModel):
    """Patch mutable fields for a tenant-owned custom tax rate.

    All fields are optional; only fields explicitly present in the request are
    updated. ``model_fields_set`` distinguishes an omitted field from an explicit
    ``null`` — this matters for ``market``, where ``null`` legitimately means
    "applies to all markets" rather than "no change".
    """

    name: str | None = None
    rate: Decimal | None = None
    market: str | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required")
        return cleaned

    @field_validator("rate")
    @classmethod
    def validate_rate(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if value < 0 or value > 100:
            raise ValueError("Rate must be between 0 and 100")
        return value
