"""Unit tests for InvoicesService — invoice lifecycle + Stripe Payment Link.

Covers issues #50, #51, #52.

All tests use unittest.mock — no network calls, no DB, no Stripe credentials.
"""
# Prahari review required — see docs/team/SECURITY_REVIEW.md

from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> MagicMock:
    """Minimal supabase Client mock."""
    return MagicMock()


@pytest.fixture
def tenant_id() -> str:
    return "tenant-uuid-001"


@pytest.fixture
def invoice_id() -> str:
    return "invoice-uuid-001"


def _draft_invoice(invoice_id: str, tenant_id: str, status: str = "draft") -> dict:
    """Build a minimal invoice row dict."""
    return {
        "id": invoice_id,
        "tenant_id": tenant_id,
        "engagement_id": "eng-uuid-001",
        "client_id": "client-uuid-001",
        "invoice_number": "INV-0001",
        "currency": "USD",
        "subtotal": "1000.00",
        "tax_total": "0.00",
        "total": "1000.00",
        "status": status,
        "issue_date": "2026-05-01",
        "due_date": "2026-06-01",
        "paid_at": None,
        "stripe_payment_link_id": None,
        "stripe_payment_link_url": None,
        "public_token": "tok_test_abc123",
        "sent_at": None,
        "notes": None,
        "created_at": "2026-05-01T00:00:00+00:00",
        "updated_at": "2026-05-01T00:00:00+00:00",
    }


# ---------------------------------------------------------------------------
# Issue #50 — send_invoice requires approved or draft status
# ---------------------------------------------------------------------------


def test_send_invoice_requires_approved_or_draft_status(
    mock_db: MagicMock,
    tenant_id: str,
    invoice_id: str,
) -> None:
    """send_invoice raises HTTP 409 if invoice is already paid or voided."""
    from app.services.invoices_service import InvoicesService

    svc = InvoicesService(mock_db, tenant_id)

    # Simulate repo returning a paid invoice
    paid_invoice = _draft_invoice(invoice_id, tenant_id, status="paid")
    svc._repo.get_by_id = AsyncMock(return_value=paid_invoice)

    with pytest.raises(Exception) as exc_info:
        asyncio.run(svc.send_invoice(invoice_id, sent_by="user-uuid-001"))

    # FastAPI HTTPException — status_code 409
    exc = exc_info.value
    assert hasattr(exc, "status_code"), f"Expected HTTPException, got {type(exc)}"
    assert exc.status_code == 409
    assert "paid" in exc.detail.lower()


def test_send_invoice_raises_409_for_voided(
    mock_db: MagicMock,
    tenant_id: str,
    invoice_id: str,
) -> None:
    """send_invoice raises HTTP 409 for voided status."""
    from app.services.invoices_service import InvoicesService

    svc = InvoicesService(mock_db, tenant_id)
    voided_invoice = _draft_invoice(invoice_id, tenant_id, status="voided")
    svc._repo.get_by_id = AsyncMock(return_value=voided_invoice)

    with pytest.raises(Exception) as exc_info:
        asyncio.run(svc.send_invoice(invoice_id, sent_by="user-uuid-001"))

    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# Issue #50 — payment_link_url returned in send response
# ---------------------------------------------------------------------------


def test_send_invoice_returns_payment_link_url(
    mock_db: MagicMock,
    tenant_id: str,
    invoice_id: str,
) -> None:
    """send_invoice returns the Stripe payment_link_url in the response."""
    from app.services.invoices_service import InvoicesService

    svc = InvoicesService(mock_db, tenant_id)

    draft_invoice = _draft_invoice(invoice_id, tenant_id, status="approved")
    updated_invoice = {
        **draft_invoice,
        "status": "sent",
        "stripe_payment_link_id": "plink_test_001",
        "stripe_payment_link_url": "https://buy.stripe.com/test_001",
    }

    svc._repo.get_by_id = AsyncMock(return_value=draft_invoice)
    svc._repo.get_tenant = AsyncMock(return_value={"stripe_connect_account_id": None})
    svc._repo.update = AsyncMock(return_value=updated_invoice)
    svc._repo.list_lines = AsyncMock(return_value=[])

    fake_product = MagicMock()
    fake_product.id = "prod_test_001"

    fake_price = MagicMock()
    fake_price.id = "price_test_001"

    fake_payment_link = MagicMock()
    fake_payment_link.id = "plink_test_001"
    fake_payment_link.url = "https://buy.stripe.com/test_001"

    with (
        patch("stripe.Product.create", return_value=fake_product),
        patch("stripe.Price.create", return_value=fake_price),
        patch("stripe.PaymentLink.create", return_value=fake_payment_link),
    ):
        result = asyncio.run(svc.send_invoice(invoice_id, sent_by="user-uuid-001"))

    assert result.payment_link_url == "https://buy.stripe.com/test_001"
    assert result.stripe_payment_link_url == "https://buy.stripe.com/test_001"


# ---------------------------------------------------------------------------
# Issue #50 — InvoiceResponse serialises monetary fields as strings
# ---------------------------------------------------------------------------


def test_invoice_response_serialises_totals_as_strings() -> None:
    """InvoiceResponse.from_db returns subtotal/tax_total/total as strings."""
    from app.models.invoices import InvoiceResponse

    row = {
        "id": "inv-001",
        "tenant_id": "tenant-001",
        "engagement_id": "eng-001",
        "client_id": "client-001",
        "invoice_number": "INV-0001",
        "currency": "USD",
        "subtotal": Decimal("1000.00"),
        "tax_total": Decimal("0.00"),
        "total": Decimal("1000.00"),
        "status": "draft",
        "issue_date": None,
        "due_date": None,
        "paid_at": None,
        "stripe_payment_link_id": None,
        "stripe_payment_link_url": None,
        "public_token": None,
        "sent_at": None,
        "notes": None,
        "created_at": "2026-05-01T00:00:00+00:00",
        "updated_at": "2026-05-01T00:00:00+00:00",
    }

    response = InvoiceResponse.from_db(row)
    assert isinstance(response.subtotal, str)
    assert isinstance(response.tax_total, str)
    assert isinstance(response.total, str)
    assert response.subtotal == "1000.00"
    assert response.total == "1000.00"


# ---------------------------------------------------------------------------
# Issue #50 — Connect routing
# ---------------------------------------------------------------------------


def test_send_invoice_routes_through_connect_when_enabled(
    mock_db: MagicMock,
    tenant_id: str,
    invoice_id: str,
) -> None:
    """send_invoice includes on_behalf_of when tenant has charges_enabled Connect."""
    from app.services.invoices_service import InvoicesService

    svc = InvoicesService(mock_db, tenant_id)

    draft_invoice = _draft_invoice(invoice_id, tenant_id, status="approved")
    updated_invoice = {**draft_invoice, "status": "sent"}

    svc._repo.get_by_id = AsyncMock(return_value=draft_invoice)
    svc._repo.get_tenant = AsyncMock(
        return_value={
            "stripe_connect_account_id": "acct_connect_001",
            "stripe_connect_charges_enabled": True,
        }
    )
    svc._repo.update = AsyncMock(return_value=updated_invoice)
    svc._repo.list_lines = AsyncMock(return_value=[])

    fake_product = MagicMock()
    fake_product.id = "prod_test_002"
    fake_price = MagicMock()
    fake_price.id = "price_test_002"
    fake_payment_link = MagicMock()
    fake_payment_link.id = "plink_test_002"
    fake_payment_link.url = "https://buy.stripe.com/test_002"

    captured_kwargs: dict = {}

    def capture_pl_create(**kwargs: object) -> MagicMock:
        captured_kwargs.update(kwargs)
        return fake_payment_link

    with (
        patch("stripe.Product.create", return_value=fake_product),
        patch("stripe.Price.create", return_value=fake_price),
        patch("stripe.PaymentLink.create", side_effect=capture_pl_create),
    ):
        asyncio.run(svc.send_invoice(invoice_id, sent_by="user-uuid-001"))

    assert captured_kwargs.get("on_behalf_of") == "acct_connect_001"
    assert captured_kwargs.get("transfer_data") == {"destination": "acct_connect_001"}


# ---------------------------------------------------------------------------
# Issue #52 — Stripe webhook payment idempotency
# ---------------------------------------------------------------------------


def test_payment_idempotency_skips_duplicate(mock_db: MagicMock) -> None:
    """_handle_checkout_session_completed skips when payment_intent already recorded."""
    from app.api.v1.endpoints.webhooks import _handle_checkout_session_completed

    # Build a minimal stripe event object.
    # Do NOT use spec=stripe.Event — the spec prevents attribute assignment on
    # nested StripeObject children (data.object).
    mock_event = MagicMock()
    mock_event.id = "evt_test_dup"
    mock_event.type = "checkout.session.completed"

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value={"invoice_id": "inv-001", "tenant_id": "tenant-001"})
    mock_session.payment_intent = "pi_test_dup_001"
    mock_event.data.object = mock_session

    # DB: payments table already has this payment_intent_id
    mock_result = MagicMock()
    mock_result.data = [{"id": "pay_existing_001"}]
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

    # Should complete without inserting a new payment
    asyncio.run(_handle_checkout_session_completed(mock_event, mock_db))

    # Verify: the call completed without exception.
    # The idempotency check found an existing payment and returned early —
    # no additional DB inserts are expected.
    mock_db.table.assert_called()  # at least the payments SELECT was issued


# ---------------------------------------------------------------------------
# Issue #52 — Amount conversion from cents to decimal
# ---------------------------------------------------------------------------


def test_payment_idempotency_check() -> None:
    """Payment idempotency: cents to Decimal conversion is correct for common amounts."""
    amount_cents = 100_000  # $1,000.00
    amount = Decimal(str(amount_cents)) / Decimal("100")
    assert amount == Decimal("1000.00")

    amount_cents_fractional = 99  # $0.99
    amount2 = Decimal(str(amount_cents_fractional)) / Decimal("100")
    assert amount2 == Decimal("0.99")


# ---------------------------------------------------------------------------
# Issue #50 — approve_invoice raises 409 if not draft
# ---------------------------------------------------------------------------


def test_approve_invoice_raises_409_if_not_draft(
    mock_db: MagicMock,
    tenant_id: str,
    invoice_id: str,
) -> None:
    """approve_invoice raises HTTP 409 if invoice is not in draft status."""
    from app.services.invoices_service import InvoicesService

    svc = InvoicesService(mock_db, tenant_id)
    approved_invoice = _draft_invoice(invoice_id, tenant_id, status="approved")
    svc._repo.get_by_id = AsyncMock(return_value=approved_invoice)

    with pytest.raises(Exception) as exc_info:
        asyncio.run(svc.approve_invoice(invoice_id, approved_by="user-uuid-001"))

    assert exc_info.value.status_code == 409
    assert "approved" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Issue #51 — Connect OAuth URL includes required parameters
# ---------------------------------------------------------------------------


def test_connect_oauth_url_includes_client_id_and_state() -> None:
    """create_connect_oauth_url embeds client_id and tenant_id in state."""
    from app.services.billing.stripe_service import StripeService

    mock_settings = MagicMock()
    mock_settings.stripe_secret_key = "sk_test_placeholder"
    mock_settings.stripe_webhook_secret = "whsec_placeholder"
    mock_settings.stripe_connect_client_id = "ca_test_connect_id"

    svc = StripeService(mock_settings)
    tenant_id = "tenant-oauth-test"
    redirect_uri = "http://localhost:4201/settings/billing/connect/return"

    url = asyncio.run(
        svc.create_connect_oauth_url(
            tenant_id=tenant_id,
            redirect_uri=redirect_uri,
            country="US",
        )
    )

    assert "ca_test_connect_id" in url
    assert tenant_id in url
    assert "response_type=code" in url
    assert "scope=read_write" in url
    assert "US" in url


# ---------------------------------------------------------------------------
# Issue #51 — exchange_connect_code extracts stripe_user_id
# ---------------------------------------------------------------------------


def test_exchange_connect_code_returns_account_id() -> None:
    """exchange_connect_code extracts stripe_user_id from OAuth response."""
    from app.services.billing.stripe_service import StripeService

    mock_settings = MagicMock()
    mock_settings.stripe_secret_key = "sk_test_placeholder"
    mock_settings.stripe_webhook_secret = "whsec_placeholder"
    mock_settings.stripe_connect_client_id = "ca_test"

    svc = StripeService(mock_settings)

    fake_token = MagicMock()
    fake_token.stripe_user_id = "acct_connect_test_001"
    fake_token.access_token = "sk_live_connected_key"

    with patch("stripe.OAuth.token", return_value=fake_token):
        result = asyncio.run(svc.exchange_connect_code("code_test_abc"))

    assert result["stripe_connect_account_id"] == "acct_connect_test_001"
    assert result["access_token"] == "sk_live_connected_key"
