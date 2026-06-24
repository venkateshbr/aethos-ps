"""Tenant tax-rate settings service."""

from __future__ import annotations

import asyncio
import re
from decimal import Decimal

from fastapi import HTTPException, status

from app.models.tax_rates import TaxRateCreate, TaxRateResponse, TaxRateUpdate
from app.services.localization_service import country_to_market, market_to_country
from supabase import Client


def _percent_from_fraction(value: object) -> str:
    fraction = Decimal(str(value))
    return str((fraction * Decimal("100")).quantize(Decimal("0.01")))


def _fraction_from_percent(value: Decimal) -> str:
    return str((value / Decimal("100")).quantize(Decimal("0.0001")))


def _custom_code(name: str) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "-", name.upper()).strip("-")
    return f"CUSTOM-{slug or 'TAX'}"


def _to_response(row: dict) -> TaxRateResponse:
    return TaxRateResponse(
        id=str(row["id"]),
        name=str(row["name"]),
        rate=_percent_from_fraction(row["rate"]),
        market=country_to_market(row.get("country")),
        is_system=row.get("tenant_id") is None or bool(row.get("is_seeded")),
        is_active=bool(row["is_active"]),
    )


class TaxRatesService:
    """Tenant-scoped tax-rate settings operations."""

    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    async def list_tax_rates(self) -> list[TaxRateResponse]:
        """Return active system rates plus all current-tenant custom rates."""

        def _fetch_system() -> list[dict]:
            return (
                self.db.table("tax_rates")
                .select("id, tenant_id, country, code, name, rate, is_active, is_seeded")
                .is_("tenant_id", "null")
                .is_("deleted_at", "null")
                .order("country")
                .execute()
                .data
                or []
            )

        def _fetch_tenant() -> list[dict]:
            return (
                self.db.table("tax_rates")
                .select("id, tenant_id, country, code, name, rate, is_active, is_seeded")
                .eq("tenant_id", self.tenant_id)
                .is_("deleted_at", "null")
                .order("country")
                .execute()
                .data
                or []
            )

        system_rows, tenant_rows = await asyncio.gather(
            asyncio.to_thread(_fetch_system),
            asyncio.to_thread(_fetch_tenant),
        )
        return [_to_response(row) for row in [*system_rows, *tenant_rows]]

    async def create_tax_rate(self, payload: TaxRateCreate) -> TaxRateResponse:
        """Create a tenant-owned tax rate from a percentage input."""

        row = {
            "tenant_id": self.tenant_id,
            "country": market_to_country(payload.market),
            "code": _custom_code(payload.name),
            "name": payload.name,
            "rate": _fraction_from_percent(payload.rate),
            "is_active": payload.is_active,
            "is_seeded": False,
            "is_default": False,
        }

        def _insert() -> dict:
            result = self.db.table("tax_rates").insert(row).execute()
            return (result.data or [])[0]

        created = await asyncio.to_thread(_insert)
        return _to_response(created)

    async def update_tax_rate(
        self,
        tax_rate_id: str,
        payload: TaxRateUpdate,
    ) -> TaxRateResponse:
        """Patch a tenant-owned custom tax rate.

        System-seeded rates have ``tenant_id IS NULL`` and are intentionally not
        matched by this update path.
        """

        def _update() -> dict | None:
            result = (
                self.db.table("tax_rates")
                .update({"is_active": payload.is_active})
                .eq("id", tax_rate_id)
                .eq("tenant_id", self.tenant_id)
                .is_("deleted_at", "null")
                .execute()
            )
            rows = result.data or []
            return rows[0] if rows else None

        updated = await asyncio.to_thread(_update)
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tax rate not found",
            )
        return _to_response(updated)
