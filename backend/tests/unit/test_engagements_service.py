"""Unit tests for EngagementService write-path invariants."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
