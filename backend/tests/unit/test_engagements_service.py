"""Unit tests for EngagementService write-path invariants."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-engagement-service-001"
ENGAGEMENT_ID = "engagement-service-001"


def _engagement_row(*, currency: str = "GBP") -> dict:
    return {
        "id": ENGAGEMENT_ID,
        "tenant_id": TENANT_ID,
        "client_id": "client-service-001",
        "name": "GBP Advisory",
        "billing_arrangement": "time_and_materials",
        "currency": currency,
        "total_value": None,
        "status": "draft",
        "start_date": None,
        "end_date": None,
        "created_at": "2026-06-22T00:00:00+00:00",
    }


def _service_with_repo_mocks(row: dict):
    from app.services.engagements_service import EngagementService

    svc = EngagementService(MagicMock(), TENANT_ID)
    svc._repo.create = AsyncMock(return_value=row)
    svc._repo.create_billing_terms = AsyncMock()
    svc._projects_repo.list = AsyncMock(return_value=[])
    svc._projects_repo.create = AsyncMock(
        return_value={
            "id": "project-general-001",
            "tenant_id": TENANT_ID,
            "engagement_id": ENGAGEMENT_ID,
            "name": "General",
            "currency": row["currency"],
            "status": "planning",
            "created_at": "2026-06-22T00:00:00+00:00",
        }
    )
    return svc


@pytest.mark.asyncio
async def test_create_engagement_creates_default_general_project() -> None:
    from app.models.engagements import EngagementCreate

    row = _engagement_row(currency="GBP")
    svc = _service_with_repo_mocks(row)

    with patch(
        "app.services.engagements_service.assert_belongs_to_tenant",
        new_callable=AsyncMock,
    ):
        result = await svc.create_engagement(
            EngagementCreate(
                client_id="client-service-001",
                name="GBP Advisory",
                billing_arrangement="time_and_materials",
                currency="GBP",
            )
        )

    assert result.id == ENGAGEMENT_ID
    svc._projects_repo.create.assert_awaited_once_with(
        {
            "engagement_id": ENGAGEMENT_ID,
            "name": "General",
            "currency": "GBP",
            "status": "planning",
        }
    )


@pytest.mark.asyncio
async def test_create_engagement_does_not_duplicate_existing_general_project() -> None:
    from app.models.engagements import EngagementCreate

    row = _engagement_row(currency="USD")
    svc = _service_with_repo_mocks(row)
    svc._projects_repo.list = AsyncMock(return_value=[{"id": "project-1", "name": "General"}])

    with patch(
        "app.services.engagements_service.assert_belongs_to_tenant",
        new_callable=AsyncMock,
    ):
        await svc.create_engagement(
            EngagementCreate(
                client_id="client-service-001",
                name="USD Advisory",
                billing_arrangement="time_and_materials",
                currency="USD",
            )
        )

    svc._projects_repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_engagement_persists_service_rate_card_description_and_terms() -> None:
    from app.models.engagements import BillingTerms, EngagementCreate

    row = {
        **_engagement_row(currency="USD"),
        "billing_arrangement": "capped_tm",
        "total_value": "75000.00",
        "description": "Advisory with capped overage",
        "service_line": "advisory",
        "rate_card_id": "rate-card-001",
        "service_catalogue_id": "service-001",
    }
    terms_row = {
        "fixed_fee_amount": None,
        "milestone_total": None,
        "retainer_monthly_amount": None,
        "retainer_floor": None,
        "retainer_rollover": False,
        "cap_amount": "75000.00",
    }
    svc = _service_with_repo_mocks(row)
    svc._repo.create_billing_terms = AsyncMock(return_value=terms_row)

    with patch(
        "app.services.engagements_service.assert_belongs_to_tenant",
        new_callable=AsyncMock,
    ) as assert_belongs:
        result = await svc.create_engagement(
            EngagementCreate(
                client_id="client-service-001",
                name="USD Advisory",
                billing_arrangement="capped_tm",
                currency="USD",
                total_value="75000",
                description="Advisory with capped overage",
                rate_card_id="rate-card-001",
                service_line="advisory",
                service_catalogue_id="service-001",
                billing_terms=BillingTerms(cap_amount="75000"),
            )
        )

    assert result.description == "Advisory with capped overage"
    assert result.rate_card_id == "rate-card-001"
    assert result.service_line == "advisory"
    assert result.service_catalogue_id == "service-001"
    assert result.billing_terms is not None
    assert result.billing_terms.cap_amount == "75000.00"
    svc._repo.create.assert_awaited_once_with(
        {
            "client_id": "client-service-001",
            "name": "USD Advisory",
            "billing_arrangement": "capped_tm",
            "currency": "USD",
            "status": "draft",
            "service_line": "advisory",
            "total_value": "75000.00",
            "description": "Advisory with capped overage",
            "rate_card_id": "rate-card-001",
            "service_catalogue_id": "service-001",
        }
    )
    svc._repo.create_billing_terms.assert_awaited_once_with(
        ENGAGEMENT_ID,
        {"cap_amount": "75000.00"},
    )
    assert_belongs.assert_any_await(
        svc._db,
        "clients",
        "client-service-001",
        TENANT_ID,
        not_found_detail="Client not found",
    )
    assert_belongs.assert_any_await(
        svc._db,
        "rate_cards",
        "rate-card-001",
        TENANT_ID,
        not_found_detail="Rate card not found",
    )
    assert_belongs.assert_any_await(
        svc._db,
        "service_catalogue",
        "service-001",
        TENANT_ID,
        not_found_detail="Service catalogue item not found",
    )


@pytest.mark.asyncio
async def test_create_engagement_persists_per_unit_billing_terms() -> None:
    from app.models.engagements import BillingTerms, EngagementCreate

    row = {
        **_engagement_row(currency="USD"),
        "billing_arrangement": "fixed_fee",
        "total_value": None,
        "service_line": "payroll",
        "service_catalogue_id": "service-payroll-001",
    }
    terms_row = {
        "fixed_fee_amount": "777.00",
        "milestone_total": None,
        "retainer_monthly_amount": None,
        "retainer_floor": None,
        "retainer_rollover": False,
        "cap_amount": None,
        "billing_unit": "per_employee",
        "unit_label": "Employees",
        "unit_quantity": "42",
        "unit_price": "18.50",
    }
    svc = _service_with_repo_mocks(row)
    svc._repo.create_billing_terms = AsyncMock(return_value=terms_row)

    with patch(
        "app.services.engagements_service.assert_belongs_to_tenant",
        new_callable=AsyncMock,
    ):
        result = await svc.create_engagement(
            EngagementCreate(
                client_id="client-service-001",
                name="Monthly Payroll",
                billing_arrangement="fixed_fee",
                currency="USD",
                service_line="payroll",
                service_catalogue_id="service-payroll-001",
                billing_terms=BillingTerms(
                    billing_unit="per_employee",
                    unit_label="Employees",
                    unit_quantity="42",
                    unit_price="18.50",
                ),
            )
        )

    assert result.billing_terms is not None
    assert result.billing_terms.fixed_fee_amount == "777.00"
    assert result.billing_terms.billing_unit == "per_employee"
    assert result.billing_terms.unit_quantity == "42"
    assert result.billing_terms.unit_price == "18.50"
    svc._repo.create_billing_terms.assert_awaited_once_with(
        ENGAGEMENT_ID,
        {
            "fixed_fee_amount": "777.00",
            "billing_unit": "per_employee",
            "unit_label": "Employees",
            "unit_quantity": "42",
            "unit_price": "18.50",
        },
    )


@pytest.mark.asyncio
async def test_create_engagement_blocks_cross_tenant_service_catalogue_item() -> None:
    from app.models.engagements import EngagementCreate

    row = _engagement_row(currency="USD")
    svc = _service_with_repo_mocks(row)

    async def fake_assert(*args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        if args[1] == "service_catalogue":
            raise HTTPException(status_code=404, detail="Service catalogue item not found")

    with patch("app.services.engagements_service.assert_belongs_to_tenant", fake_assert):
        with pytest.raises(HTTPException) as exc:
            await svc.create_engagement(
                EngagementCreate(
                    client_id="client-service-001",
                    name="USD Advisory",
                    billing_arrangement="fixed_fee",
                    currency="USD",
                    service_catalogue_id="foreign-service-001",
                )
            )

    assert exc.value.status_code == 404
    svc._repo.create.assert_not_awaited()
