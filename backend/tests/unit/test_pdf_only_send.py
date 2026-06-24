"""Unit tests for PDF-only invoice send path (#178).

When Stripe is not configured (empty stripe_secret_key), send_invoice
marks the invoice as 'sent' without creating a payment link.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _draft_invoice(invoice_id: str, tenant_id: str) -> dict:
    return {
        "id": invoice_id,
        "tenant_id": tenant_id,
        "engagement_id": "eng-001",
        "client_id": "client-001",
        "invoice_number": "INV-0001",
        "currency": "USD",
        "subtotal": "1000.00",
        "tax_total": "0.00",
        "total": "1000.00",
        "status": "approved",
        "issue_date": None,
        "due_date": None,
        "paid_at": None,
        "stripe_payment_link_id": None,
        "stripe_payment_link_url": None,
        "public_token": "tok-abc",
        "sent_at": None,
        "notes": None,
        "created_at": "2026-06-01T00:00:00+00:00",
        "updated_at": "2026-06-01T00:00:00+00:00",
        "base_total": None,
        "type": "invoice",
        "deleted_at": None,
    }


def test_send_invoice_pdf_only_when_stripe_not_configured() -> None:
    """send_invoice marks invoice 'sent' without payment link when Stripe secret absent."""
    from app.services.invoices_service import InvoicesService

    mock_db = MagicMock()
    tenant_id = "tenant-001"
    invoice_id = "inv-001"

    svc = InvoicesService(mock_db, tenant_id)

    draft = _draft_invoice(invoice_id, tenant_id)
    sent = {**draft, "status": "sent"}

    svc._repo = MagicMock()
    svc._repo.get_by_id = AsyncMock(return_value=draft)
    svc._repo.get_tenant = AsyncMock(return_value={"stripe_connect_account_id": None})
    svc._repo.update = AsyncMock(return_value=sent)
    svc._repo.list_lines = AsyncMock(return_value=[])

    with patch("app.services.invoices_service.settings") as mock_settings:
        mock_settings.stripe_secret_key = ""  # not configured
        mock_settings.frontend_base_url = "https://app.aethos.test"
        result = asyncio.run(svc.send_invoice(invoice_id, sent_by="user-001"))

    assert result.status == "sent"
    # No payment link on the response
    assert result.payment_link_url is None
    # update stamps sent_at for reconciliation eligibility, but no Stripe fields.
    update_payload = svc._repo.update.call_args[0][1]
    assert update_payload["status"] == "sent"
    assert update_payload["sent_at"]
    assert "stripe_payment_link_id" not in update_payload


def test_send_invoice_uses_stripe_when_configured() -> None:
    """send_invoice creates a Stripe Payment Link when stripe_secret_key is set."""
    from app.services.invoices_service import InvoicesService

    mock_db = MagicMock()
    tenant_id = "tenant-001"
    invoice_id = "inv-002"

    svc = InvoicesService(mock_db, tenant_id)

    draft = _draft_invoice(invoice_id, tenant_id)
    sent = {
        **draft,
        "status": "sent",
        "stripe_payment_link_id": "plink_test",
        "stripe_payment_link_url": "https://buy.stripe.com/test",
    }

    svc._repo = MagicMock()
    svc._repo.get_by_id = AsyncMock(return_value=draft)
    svc._repo.get_tenant = AsyncMock(return_value={"stripe_connect_account_id": None})
    svc._repo.update = AsyncMock(return_value=sent)
    svc._repo.list_lines = AsyncMock(return_value=[])

    fake_product = MagicMock()
    fake_product.id = "prod_001"
    fake_price = MagicMock()
    fake_price.id = "price_001"
    fake_pl = MagicMock()
    fake_pl.id = "plink_test"
    fake_pl.url = "https://buy.stripe.com/test"

    with (
        patch("stripe.Product.create", return_value=fake_product),
        patch("stripe.Price.create", return_value=fake_price),
        patch("stripe.PaymentLink.create", return_value=fake_pl),
        patch("app.services.invoices_service.settings") as mock_settings,
    ):
        mock_settings.stripe_secret_key = "sk_test_placeholder"
        mock_settings.frontend_base_url = "https://app.aethos.test"
        result = asyncio.run(svc.send_invoice(invoice_id, sent_by="user-001"))

    assert result.status == "sent"
    assert result.payment_link_url == "https://buy.stripe.com/test"
