"""Business logic for the Engagements resource."""

from __future__ import annotations

import logging

from app.models.engagements import (
    BillingTerms,
    EngagementCreate,
    EngagementResponse,
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
        if data.total_value is not None:
            # Quantise on the way in so the DB row already has 2dp precision —
            # downstream readers don't have to worry about "100000.0" coming
            # back as a stale value.
            from app.domain.money import serialise_money
            eng_data["total_value"] = serialise_money(data.total_value)
        if data.start_date is not None:
            eng_data["start_date"] = data.start_date.isoformat()
        if data.end_date is not None:
            eng_data["end_date"] = data.end_date.isoformat()
        if data.rate_card_id is not None:
            eng_data["rate_card_id"] = data.rate_card_id

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


def _billing_terms_to_dict(terms: BillingTerms) -> dict:
    from app.domain.money import serialise_money

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
