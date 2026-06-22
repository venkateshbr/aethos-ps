"""Unit tests for EngagementService.get_engagement_summary and service_line field.

All tests use MagicMock — no network calls, no real DB, no credentials.

The service delegates invoice and WIP aggregation to repo methods:
  - repo.get_invoice_summary → {billed_to_date, invoice_count, last_invoice_date}
  - repo.get_wip_summary     → {wip_hours, wip_value}

Tests mock those repo methods directly so the service logic is cleanly isolated.

Issues: #247, #237
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-test-summary-001"
ENG_ID = "eng-summary-uuid-001"


# ---------------------------------------------------------------------------
# Shared engagement DB row factory
# ---------------------------------------------------------------------------


def _eng_row(
    *,
    total_value: str | None = "50000.00",
    currency: str = "GBP",
    rate_card_id: str | None = None,
) -> dict:
    return {
        "id": ENG_ID,
        "tenant_id": TENANT_ID,
        "client_id": "client-001",
        "name": "Henderson Audit 2026",
        "billing_arrangement": "fixed_fee",
        "currency": currency,
        "total_value": total_value,
        "status": "active",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "created_at": "2026-01-01T00:00:00+00:00",
        "rate_card_id": rate_card_id,
        "service_line": "accounting",
    }


# ---------------------------------------------------------------------------
# Service factory with repo methods mocked as coroutines
# ---------------------------------------------------------------------------


def _make_svc_with_repo_mocks(
    eng_row: dict | None,
    invoice_summary: dict,
    wip_summary: dict,
):
    """Build an EngagementService with repo methods mocked to return fixed data."""
    from app.services.engagements_service import EngagementService

    mock_db = MagicMock()
    svc = EngagementService(mock_db, TENANT_ID)

    # Replace repo methods with async mocks
    svc._repo.get = AsyncMock(return_value=eng_row)
    svc._repo.get_invoice_summary = AsyncMock(return_value=invoice_summary)
    svc._repo.get_wip_summary = AsyncMock(return_value=wip_summary)

    return svc


# ---------------------------------------------------------------------------
# 1. Summary with a single paid invoice
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_with_paid_invoice() -> None:
    """billed_to_date must equal the paid invoice total; invoice_count = 1."""
    svc = _make_svc_with_repo_mocks(
        eng_row=_eng_row(total_value="50000.00"),
        invoice_summary={
            "billed_to_date": Decimal("21000.00"),
            "invoice_count": 1,
            "last_invoice_date": "2026-03-15",
        },
        wip_summary={"wip_hours": 0.0, "wip_value": "0.00"},
    )

    summary = await svc.get_engagement_summary(ENG_ID)

    assert summary is not None
    assert summary.engagement_id == ENG_ID
    assert summary.engagement_name == "Henderson Audit 2026"
    assert summary.billed_to_date == "21000.00"
    assert summary.invoice_count == 1
    assert summary.last_invoice_date == "2026-03-15"
    assert summary.total_value == "50000.00"
    # 50000 - 21000 = 29000
    assert summary.remaining_value == "29000.00"
    # 21000 / 50000 * 100 = 42.0
    assert summary.billed_pct == pytest.approx(42.0, abs=0.1)
    assert summary.wip_hours == 0.0
    assert summary.wip_value == "0.00"
    assert summary.currency == "GBP"


# ---------------------------------------------------------------------------
# 2. Summary with unbilled WIP time entries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_wip() -> None:
    """wip_hours and wip_value come from repo.get_wip_summary; total_value=None."""
    svc = _make_svc_with_repo_mocks(
        eng_row=_eng_row(total_value=None, rate_card_id="rc-abc-001"),
        invoice_summary={
            "billed_to_date": Decimal("0"),
            "invoice_count": 0,
            "last_invoice_date": None,
        },
        # 4.0 + 3.5 + 2.5 = 10.0 hours × 175.00 = 1750.00
        wip_summary={"wip_hours": 10.0, "wip_value": "1750.00"},
    )

    summary = await svc.get_engagement_summary(ENG_ID)

    assert summary is not None
    assert summary.wip_hours == pytest.approx(10.0)
    assert summary.wip_value == "1750.00"
    assert summary.billed_to_date == "0.00"
    assert summary.invoice_count == 0
    # No total_value → remaining and billed_pct must both be None
    assert summary.total_value is None
    assert summary.remaining_value is None
    assert summary.billed_pct is None


# ---------------------------------------------------------------------------
# 3. Summary for a brand-new engagement with no invoices and no WIP
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_no_invoices() -> None:
    """New engagement: billed_to_date = '0.00', wip = 0, invoice_count = 0."""
    svc = _make_svc_with_repo_mocks(
        eng_row=_eng_row(total_value="30000.00"),
        invoice_summary={
            "billed_to_date": Decimal("0"),
            "invoice_count": 0,
            "last_invoice_date": None,
        },
        wip_summary={"wip_hours": 0.0, "wip_value": "0.00"},
    )

    summary = await svc.get_engagement_summary(ENG_ID)

    assert summary is not None
    assert summary.billed_to_date == "0.00"
    assert summary.invoice_count == 0
    assert summary.last_invoice_date is None
    assert summary.wip_hours == 0.0
    assert summary.wip_value == "0.00"
    assert summary.remaining_value == "30000.00"
    assert summary.billed_pct == 0.0


# ---------------------------------------------------------------------------
# 4. get_engagement_summary returns None for unknown engagement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_returns_none_for_missing_engagement() -> None:
    """Service returns None when engagement is not found by the repo."""
    svc = _make_svc_with_repo_mocks(
        eng_row=None,
        invoice_summary={},
        wip_summary={},
    )

    result = await svc.get_engagement_summary("does-not-exist")
    assert result is None


# ---------------------------------------------------------------------------
# 5. service_line field — EngagementCreate model
# ---------------------------------------------------------------------------


def test_service_line_create_valid() -> None:
    """EngagementCreate accepts all valid service_line values."""
    from app.models.engagements import EngagementCreate

    for value in ("accounting", "tax", "cosec", "payroll", "advisory", "other"):
        eng = EngagementCreate(
            client_id="client-001",
            name=f"{value} Engagement",
            billing_arrangement="fixed_fee",
            currency="GBP",
            service_line=value,  # type: ignore[arg-type]
        )
        assert eng.service_line == value


def test_service_line_create_none_allowed() -> None:
    """service_line is optional; None is the default."""
    from app.models.engagements import EngagementCreate

    eng = EngagementCreate(
        client_id="client-001",
        name="Open Engagement",
        billing_arrangement="time_and_materials",
    )
    assert eng.service_line is None


def test_service_line_create_invalid_raises() -> None:
    """An unrecognised service_line value raises a ValidationError."""
    from pydantic import ValidationError

    from app.models.engagements import EngagementCreate

    with pytest.raises(ValidationError):
        EngagementCreate(
            client_id="client-001",
            name="Bad Service Line",
            billing_arrangement="fixed_fee",
            service_line="litigation",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# 6. service_line field — EngagementResponse model
# ---------------------------------------------------------------------------


def test_service_line_response_roundtrip() -> None:
    """EngagementResponse.from_db propagates service_line from the DB row."""
    from app.models.engagements import EngagementResponse

    row = {
        "id": ENG_ID,
        "tenant_id": TENANT_ID,
        "client_id": "client-001",
        "name": "Payroll Annual",
        "billing_arrangement": "retainer",
        "currency": "USD",
        "total_value": None,
        "status": "active",
        "start_date": None,
        "end_date": None,
        "created_at": "2026-06-01T00:00:00+00:00",
        "service_line": "payroll",
    }
    resp = EngagementResponse.from_db(row)
    assert resp.service_line == "payroll"


def test_service_line_response_none_when_absent() -> None:
    """EngagementResponse.from_db returns service_line=None when key is missing."""
    from app.models.engagements import EngagementResponse

    row = {
        "id": ENG_ID,
        "tenant_id": TENANT_ID,
        "client_id": "client-001",
        "name": "COSEC Engagement",
        "billing_arrangement": "time_and_materials",
        "currency": "SGD",
        "total_value": None,
        "status": "draft",
        "start_date": None,
        "end_date": None,
        "created_at": "2026-06-01T00:00:00+00:00",
        # no service_line key at all
    }
    resp = EngagementResponse.from_db(row)
    assert resp.service_line is None


# ---------------------------------------------------------------------------
# 7. EngagementSummary model construction
# ---------------------------------------------------------------------------


def test_engagement_summary_model_fields() -> None:
    """EngagementSummary accepts all expected fields."""
    from app.models.engagements import EngagementSummary

    s = EngagementSummary(
        engagement_id=ENG_ID,
        engagement_name="Test Engagement",
        total_value="100000.00",
        currency="USD",
        billed_to_date="50000.00",
        billed_pct=50.0,
        wip_hours=20.0,
        wip_value="3500.00",
        remaining_value="50000.00",
        invoice_count=3,
        last_invoice_date="2026-05-31",
    )
    assert s.engagement_id == ENG_ID
    assert s.billed_pct == 50.0
    assert s.wip_hours == 20.0
    assert s.invoice_count == 3
