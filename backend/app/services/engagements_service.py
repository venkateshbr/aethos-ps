"""Business logic for the Engagements resource."""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal

from app.domain.money import serialise_money
from app.models.engagements import (
    BillingTerms,
    EngagementCreate,
    EngagementResponse,
    EngagementSummary,
)
from app.repositories.engagements_repo import EngagementRepository
from app.services._validation import assert_belongs_to_tenant
from supabase import Client

logger = logging.getLogger(__name__)


class EngagementService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id
        self._repo = EngagementRepository(db, tenant_id)

    async def list_engagements(
        self,
        status: str | None = None,
        client_id: str | None = None,
    ) -> list[EngagementResponse]:
        rows = await self._repo.list(status=status, client_id=client_id)
        return [EngagementResponse.from_db(r) for r in rows]

    async def get_engagement(self, id: str) -> EngagementResponse | None:
        row = await self._repo.get(id)
        if row is None:
            return None
        terms_row = await self._repo.get_billing_terms(id)
        return EngagementResponse.from_db(row, terms_row)

    async def create_engagement(self, data: EngagementCreate) -> EngagementResponse:
        # Bug #92: tenant A must not be able to attach tenant B's client_id to
        # their engagement. Verify the FK belongs to this tenant before insert.
        await assert_belongs_to_tenant(
            self._db,
            "clients",
            data.client_id,
            self._tenant_id,
            not_found_detail="Client not found",
        )
        # rate_card_id is optional but also tenant-scoped — guard it too.
        if data.rate_card_id is not None:
            await assert_belongs_to_tenant(
                self._db,
                "rate_cards",
                data.rate_card_id,
                self._tenant_id,
                not_found_detail="Rate card not found",
            )

        eng_data: dict = {
            "client_id": data.client_id,
            "name": data.name,
            "billing_arrangement": data.billing_arrangement,
            "currency": data.currency,
            "status": "draft",
        }
        if data.service_line is not None:
            eng_data["service_line"] = data.service_line
        if data.total_value is not None:
            # Quantise on the way in so the DB row already has 2dp precision —
            # downstream readers don't have to worry about "100000.0" coming
            # back as a stale value.
            eng_data["total_value"] = serialise_money(data.total_value)
        if data.start_date is not None:
            eng_data["start_date"] = data.start_date.isoformat()
        if data.end_date is not None:
            eng_data["end_date"] = data.end_date.isoformat()
        if data.rate_card_id is not None:
            eng_data["rate_card_id"] = data.rate_card_id
        if data.service_catalogue_id is not None:
            # Guard: service_catalogue_id must belong to this tenant.
            await assert_belongs_to_tenant(
                self._db,
                "service_catalogue",
                data.service_catalogue_id,
                self._tenant_id,
                not_found_detail="Service catalogue item not found",
            )
            eng_data["service_catalogue_id"] = data.service_catalogue_id

        row = await self._repo.create(eng_data)
        engagement_id = str(row["id"])

        terms_row: dict | None = None
        if data.billing_terms is not None:
            terms_payload = _billing_terms_to_dict(data.billing_terms)
            terms_row = await self._repo.create_billing_terms(engagement_id, terms_payload)

        return EngagementResponse.from_db(row, terms_row)

    async def update_engagement_status(
        self,
        id: str,
        status: str,
    ) -> EngagementResponse | None:
        row = await self._repo.update_status(id, status)
        if row is None:
            return None
        terms_row = await self._repo.get_billing_terms(id)
        return EngagementResponse.from_db(row, terms_row)

    async def get_engagement_summary(self, engagement_id: str) -> EngagementSummary | None:
        """Return a financial health snapshot for a single engagement.

        Computes in parallel:
        - billed_to_date: SUM of invoice totals for approved/sent/paid invoices
        - invoice_count / last_invoice_date: derived from same query
        - wip_hours + wip_value: unbilled billable hours via repo (resolves
          employee bill rates and assignment override rates)
        - remaining_value: total_value - billed_to_date (fixed fee only; None for T&M)
        - billed_pct: billed_to_date / total_value x 100 (None when no total_value)
        """
        # Fetch the engagement row first — it drives everything else.
        eng_row = await self._repo.get(engagement_id)
        if eng_row is None:
            return None

        # Run invoice and WIP aggregation concurrently.
        invoice_summary, wip_summary = await asyncio.gather(
            self._repo.get_invoice_summary(engagement_id),
            self._repo.get_wip_summary(engagement_id),
        )

        billed_to_date: Decimal = invoice_summary["billed_to_date"]
        invoice_count: int = invoice_summary["invoice_count"]
        last_invoice_date: str | None = invoice_summary["last_invoice_date"]

        wip_hours: float = wip_summary["wip_hours"]
        wip_value_str: str = wip_summary["wip_value"]

        # remaining_value and billed_pct require total_value to be set.
        total_value_raw = eng_row.get("total_value")
        total_value_dec: Decimal | None = (
            Decimal(str(total_value_raw)) if total_value_raw is not None else None
        )
        remaining_value: Decimal | None = None
        billed_pct: float | None = None
        if total_value_dec is not None:
            remaining_value = (total_value_dec - billed_to_date).quantize(Decimal("0.01"))
            if total_value_dec > Decimal("0"):
                billed_pct = float(
                    (billed_to_date / total_value_dec * 100).quantize(Decimal("0.01"))
                )
            else:
                billed_pct = 0.0

        return EngagementSummary(
            engagement_id=str(eng_row["id"]),
            engagement_name=eng_row["name"],
            total_value=serialise_money(total_value_dec),
            currency=eng_row["currency"],
            billed_to_date=serialise_money(billed_to_date),  # type: ignore[arg-type]
            billed_pct=billed_pct,
            wip_hours=wip_hours,
            wip_value=wip_value_str,
            remaining_value=serialise_money(remaining_value),
            invoice_count=invoice_count,
            last_invoice_date=last_invoice_date,
        )


def _billing_terms_to_dict(terms: BillingTerms) -> dict:
    result: dict = {}
    if terms.fixed_fee_amount is not None:
        result["fixed_fee_amount"] = serialise_money(terms.fixed_fee_amount)
    if terms.retainer_monthly_amount is not None:
        result["retainer_monthly_amount"] = serialise_money(terms.retainer_monthly_amount)
    if terms.retainer_floor is not None:
        result["retainer_floor"] = serialise_money(terms.retainer_floor)
    if terms.cap_amount is not None:
        result["cap_amount"] = serialise_money(terms.cap_amount)
    return result
