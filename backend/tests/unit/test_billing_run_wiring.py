"""Unit tests for billing_run approve → invoice drafting wiring (#198).

The approve endpoint should:
1. Update billing run status to "approved"
2. For each retainer engagement in the run's engagement_filter: call draft_invoice
3. Create actual invoice rows via InvoicesService

All DB calls are mocked. No real DB or Stripe needed.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _billing_run_row(
    run_id: str = "run-001",
    tenant_id: str = "tenant-001",
    status: str = "draft",
    engagement_ids: list[str] | None = None,
) -> dict:
    return {
        "id": run_id,
        "tenant_id": tenant_id,
        "name": "Monthly billing June 2026",
        "period_start": "2026-06-01",
        "period_end": "2026-06-30",
        "status": status,
        "created_by_agent": None,
        "summary": {"retainer_engagement_count": len(engagement_ids or [])},
        "engagement_filter": {"engagement_ids": engagement_ids or []},
        "created_at": "2026-06-01T00:00:00+00:00",
        "updated_at": "2026-06-01T00:00:00+00:00",
        "deleted_at": None,
    }


def _make_invoice_draft(engagement_id: str = "eng-001") -> MagicMock:
    """Create a mock InvoiceDraft as returned by draft_invoice."""
    from app.agents.invoice_drafter_agent import InvoiceDraft, InvoiceLineItem

    return InvoiceDraft(
        engagement_id=engagement_id,
        client_id="client-001",
        currency="USD",
        lines=[
            InvoiceLineItem(
                description="Monthly Retainer — June 2026",
                quantity=Decimal("1"),
                unit_price=Decimal("3000.00"),
                amount=Decimal("3000.00"),
                service_catalogue_id="svc-001",
            )
        ],
        subtotal=Decimal("3000.00"),
        tax_total=Decimal("0"),
        total=Decimal("3000.00"),
        billing_arrangement="retainer",
        summary="Retainer invoice for Test Engagement",
        confidence=0.95,
    )


# ---------------------------------------------------------------------------
# Test 1: approving a billing run triggers draft_invoice for each engagement
# ---------------------------------------------------------------------------


def test_approve_billing_run_calls_draft_invoice_for_each_engagement() -> None:
    """When a billing run is approved, draft_invoice is called for each
    engagement in the run's engagement_filter.engagement_ids."""
    from app.agents.base import AgentDeps
    from app.api.v1.endpoints.billing_runs import _draft_invoices_for_run

    engagement_ids = ["eng-001", "eng-002"]
    run = _billing_run_row(engagement_ids=engagement_ids)
    mock_db = MagicMock()
    deps = AgentDeps(tenant_id="tenant-001", user_id="user-001", db=mock_db)

    drafts_called: list[str] = []

    def _fake_draft(eng_id: str, d: AgentDeps, **kwargs: object) -> object:
        drafts_called.append(eng_id)
        return _make_invoice_draft(eng_id)

    with patch("app.api.v1.endpoints.billing_runs.draft_invoice", side_effect=_fake_draft):
        asyncio.run(_draft_invoices_for_run(run, deps, mock_invoice_svc=None))

    assert set(drafts_called) == {"eng-001", "eng-002"}


# ---------------------------------------------------------------------------
# Test 2: each draft is persisted as an invoice row
# ---------------------------------------------------------------------------


def test_approve_billing_run_creates_invoice_for_each_draft() -> None:
    """For each InvoiceDraft returned, an invoice must be created via InvoicesService."""
    from app.agents.base import AgentDeps
    from app.api.v1.endpoints.billing_runs import _draft_invoices_for_run

    engagement_ids = ["eng-001", "eng-002"]
    run = _billing_run_row(engagement_ids=engagement_ids)
    mock_db = MagicMock()
    deps = AgentDeps(tenant_id="tenant-001", user_id="user-001", db=mock_db)

    mock_invoice_svc = MagicMock()
    mock_invoice_svc.create_invoice = AsyncMock(return_value=MagicMock())

    def _fake_draft(eng_id: str, d: object, **kwargs: object) -> object:
        return _make_invoice_draft(eng_id)

    with patch("app.api.v1.endpoints.billing_runs.draft_invoice", side_effect=_fake_draft):
        asyncio.run(_draft_invoices_for_run(run, deps, mock_invoice_svc=mock_invoice_svc))

    # create_invoice must have been called once per engagement
    assert mock_invoice_svc.create_invoice.call_count == 2
    first_invoice = mock_invoice_svc.create_invoice.call_args_list[0][0][0]
    assert first_invoice.lines[0].service_catalogue_id == "svc-001"


# ---------------------------------------------------------------------------
# Test 3: approve endpoint with no engagement_ids does not call draft_invoice
# ---------------------------------------------------------------------------


def test_approve_billing_run_no_engagements_skips_drafting() -> None:
    """If engagement_filter has no engagement_ids, draft_invoice is not called."""
    from app.agents.base import AgentDeps
    from app.api.v1.endpoints.billing_runs import _draft_invoices_for_run

    run = _billing_run_row(engagement_ids=[])
    mock_db = MagicMock()
    deps = AgentDeps(tenant_id="tenant-001", user_id="user-001", db=mock_db)

    with patch(
        "app.api.v1.endpoints.billing_runs.draft_invoice"
    ) as mock_draft:
        asyncio.run(_draft_invoices_for_run(run, deps, mock_invoice_svc=None))

    mock_draft.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: draft_invoice error for one engagement is logged, run continues
# ---------------------------------------------------------------------------


def test_approve_billing_run_draft_error_does_not_abort_run() -> None:
    """If draft_invoice raises for one engagement, other engagements are still drafted."""
    from app.agents.base import AgentDeps
    from app.api.v1.endpoints.billing_runs import _draft_invoices_for_run

    engagement_ids = ["eng-001", "eng-fail", "eng-003"]
    run = _billing_run_row(engagement_ids=engagement_ids)
    mock_db = MagicMock()
    deps = AgentDeps(tenant_id="tenant-001", user_id="user-001", db=mock_db)

    successful_drafts: list[str] = []

    def _fake_draft(eng_id: str, d: object, **kwargs: object) -> object:
        if eng_id == "eng-fail":
            raise RuntimeError("Simulated drafting failure")
        successful_drafts.append(eng_id)
        return _make_invoice_draft(eng_id)

    mock_invoice_svc = MagicMock()
    mock_invoice_svc.create_invoice = AsyncMock(return_value=MagicMock())

    with patch("app.api.v1.endpoints.billing_runs.draft_invoice", side_effect=_fake_draft):
        # Should not raise even though one engagement fails
        asyncio.run(_draft_invoices_for_run(run, deps, mock_invoice_svc=mock_invoice_svc))

    assert "eng-001" in successful_drafts
    assert "eng-003" in successful_drafts
    assert "eng-fail" not in successful_drafts


@pytest.mark.asyncio
async def test_inbox_approval_materialises_billing_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inbox approval for scheduled billing runs reuses the billing-run draft path."""
    from app.services.inbox_service import InboxService

    run = _billing_run_row(engagement_ids=["eng-001"])
    updated = {**run, "status": "approved"}

    class _Repo:
        def __init__(self, _db: object, _tenant_id: str) -> None:
            self.updated_with: dict | None = None

        async def get_by_id(self, run_id: str) -> dict | None:
            assert run_id == "run-001"
            return run

        async def update(self, run_id: str, patch: dict) -> dict | None:
            assert run_id == "run-001"
            self.updated_with = patch
            return updated

    repo = _Repo(MagicMock(), "tenant-001")
    draft = AsyncMock()

    monkeypatch.setattr(
        "app.repositories.billing_runs_repo.BillingRunsRepository",
        lambda _db, _tenant_id: repo,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.billing_runs._draft_invoices_for_run",
        draft,
    )

    svc = InboxService.__new__(InboxService)
    svc._db = MagicMock()
    svc._tenant_id = "tenant-001"

    result = await svc._materialise_billing_run({"billing_run_id": "run-001"})

    assert result == {"entity_type": "billing_run", "entity_id": "run-001"}
    assert repo.updated_with == {"status": "approved"}
    draft.assert_awaited_once()
