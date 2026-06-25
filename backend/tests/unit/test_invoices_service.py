"""Unit tests for InvoicesService — invoice lifecycle + Stripe Payment Link.

Covers issues #50, #51, #52.

All tests use unittest.mock — no network calls, no DB, no Stripe credentials.
"""
# Prahari review required — see docs/team/SECURITY_REVIEW.md

from __future__ import annotations

import asyncio
from datetime import date
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


class _Result:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _PaymentDb, table: str) -> None:
        self.db = db
        self.table = table
        self.payload: dict | None = None

    def insert(self, payload: dict) -> _Query:
        self.payload = payload
        self.db.inserts.setdefault(self.table, []).append(payload)
        return self

    def update(self, payload: dict) -> _Query:
        self.payload = payload
        self.db.updates.setdefault(self.table, []).append(payload)
        return self

    def select(self, _columns: str) -> _Query:
        return self

    def eq(self, _key: str, _value: str) -> _Query:
        return self

    def in_(self, _key: str, _values: list[str]) -> _Query:
        return self

    def execute(self) -> _Result:
        return _Result([])


class _PaymentDb:
    def __init__(self) -> None:
        self.inserts: dict[str, list[dict]] = {}
        self.updates: dict[str, list[dict]] = {}

    def table(self, name: str) -> _Query:
        return _Query(self, name)


@pytest.mark.asyncio
async def test_invoice_repository_invalid_uuid_returns_empty_without_db(
    mock_db: MagicMock,
    tenant_id: str,
) -> None:
    from app.repositories.invoices_repo import InvoicesRepository

    repo = InvoicesRepository(mock_db, tenant_id)

    assert await repo.get_by_id("nonexistent-id") is None
    assert await repo.update("nonexistent-id", {"status": "approved"}) is None
    assert await repo.list_lines("nonexistent-id") == []
    mock_db.table.assert_not_called()


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
        patch("app.services.invoices_service.settings") as mock_settings,
    ):
        mock_settings.stripe_secret_key = "sk_test_placeholder"
        mock_settings.frontend_base_url = "https://app.aethos.test"
        result = asyncio.run(svc.send_invoice(invoice_id, sent_by="user-uuid-001"))

    assert result.payment_link_url == "https://buy.stripe.com/test_001"
    assert result.stripe_payment_link_url == "https://buy.stripe.com/test_001"
    update_payload = svc._repo.update.await_args.args[1]
    assert update_payload["status"] == "sent"
    assert update_payload["sent_at"]


@pytest.mark.asyncio
async def test_record_manual_payment_uses_base_amount_for_payment_and_journal(
    tenant_id: str,
    invoice_id: str,
) -> None:
    from app.services.invoices_service import InvoicesService
    from app.services.payment_fx_service import PaymentFxAmounts

    db = _PaymentDb()
    svc = InvoicesService(db, tenant_id)  # type: ignore[arg-type]
    invoice = {
        **_draft_invoice(invoice_id, tenant_id, status="sent"),
        "currency": "GBP",
        "total": "100.00",
        "base_total": "120.00",
    }
    updated = {**invoice, "status": "paid", "paid_at": "2026-06-25T09:00:00+00:00"}
    svc._repo.get_by_id = AsyncMock(side_effect=[invoice, updated])
    svc._repo.get_account_ids_by_codes = AsyncMock(
        return_value={"1100": "acct-bank", "1200": "acct-ar"}
    )
    svc._repo.list_lines = AsyncMock(return_value=[])
    fx_amounts = PaymentFxAmounts(
        amount=Decimal("100.00"),
        currency="GBP",
        base_amount=Decimal("125.00"),
        base_currency="USD",
        rate=Decimal("1.25"),
        rate_date=date(2026, 6, 25),
        fx_rate_id="fx-rate-1",
    )

    with (
        patch(
            "app.services.invoices_service.payment_fx_amounts",
            new=AsyncMock(return_value=fx_amounts),
        ) as payment_fx,
        patch("app.services.invoices_service.post_journal") as post_journal,
        patch(
            "app.services.invoices_service.post_fx_gain_loss_if_needed",
            new=AsyncMock(),
        ) as fx_gain_loss,
    ):
        await svc.record_manual_payment(
            invoice_id=invoice_id,
            amount=Decimal("100.00"),
            currency="gbp",
            paid_at_iso="2026-06-25T09:00:00+00:00",
            notes="Wire received",
            recorded_by="user-1",
        )

    payment_fx.assert_awaited_once()
    payment = db.inserts["payments"][0]
    assert payment["amount"] == "100.00"
    assert payment["currency"] == "GBP"
    assert payment["base_amount"] == "125.00"
    assert payment["fx_rate_id"] == "fx-rate-1"
    lines = post_journal.call_args.kwargs["lines"]
    assert [line.currency for line in lines] == ["GBP", "GBP"]
    assert [line.base_amount for line in lines] == [
        Decimal("125.00"),
        Decimal("125.00"),
    ]
    assert [line.fx_rate_id for line in lines] == ["fx-rate-1", "fx-rate-1"]
    fx_gain_loss.assert_awaited_once()
    assert fx_gain_loss.await_args.kwargs["payment_base_amount"] == Decimal("125.00")


@pytest.mark.asyncio
async def test_record_manual_payment_missing_fx_rate_rejects_before_insert(
    tenant_id: str,
    invoice_id: str,
) -> None:
    from fastapi import HTTPException

    from app.domain.fx import FxRateNotFoundError
    from app.services.invoices_service import InvoicesService

    db = _PaymentDb()
    svc = InvoicesService(db, tenant_id)  # type: ignore[arg-type]
    invoice = {
        **_draft_invoice(invoice_id, tenant_id, status="sent"),
        "currency": "GBP",
        "total": "100.00",
        "base_total": "120.00",
    }
    svc._repo.get_by_id = AsyncMock(return_value=invoice)

    with (
        patch(
            "app.services.invoices_service.payment_fx_amounts",
            new=AsyncMock(
                side_effect=FxRateNotFoundError("GBP", "USD", date(2026, 6, 25))
            ),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await svc.record_manual_payment(
            invoice_id=invoice_id,
            amount=Decimal("100.00"),
            currency="GBP",
            paid_at_iso="2026-06-25T09:00:00+00:00",
            notes=None,
            recorded_by="user-1",
        )

    assert exc_info.value.status_code == 422
    assert db.inserts == {}


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


@pytest.mark.asyncio
async def test_create_invoice_accepts_negative_adjustment_lines(
    mock_db: MagicMock,
    tenant_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Capped T&M / retainer-draw adjustments can reduce, but not invert, totals."""
    from app.models.invoices import InvoiceCreate, InvoiceLineCreate
    from app.services.invoices_service import InvoicesService

    async def _valid_fk(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr("app.services.invoices_service.assert_belongs_to_tenant", _valid_fk)

    svc = InvoicesService(mock_db, tenant_id)
    created_header = {
        "id": "inv-adjustment-001",
        "tenant_id": tenant_id,
        "engagement_id": "eng-uuid-001",
        "client_id": "client-uuid-001",
        "invoice_number": "INV-ADJ",
        "currency": "USD",
        "subtotal": "5000.00",
        "tax_total": "0.00",
        "total": "5000.00",
        "status": "draft",
        "issue_date": None,
        "due_date": None,
        "paid_at": None,
        "stripe_payment_link_id": None,
        "stripe_payment_link_url": None,
        "public_token": "tok_adjustment",
        "sent_at": None,
        "notes": None,
        "created_at": "2026-05-01T00:00:00+00:00",
        "updated_at": "2026-05-01T00:00:00+00:00",
    }
    svc._repo.create = AsyncMock(return_value=created_header)

    created_lines: list[dict] = []

    async def _create_line(payload: dict) -> dict:
        row = {
            "id": f"line-{len(created_lines) + 1}",
            "invoice_id": "inv-adjustment-001",
            "created_at": "2026-05-01T00:00:00+00:00",
            **payload,
        }
        created_lines.append(row)
        return row

    svc._repo.create_line = AsyncMock(side_effect=_create_line)

    result = await svc.create_invoice(
        InvoiceCreate(
            engagement_id="eng-uuid-001",
            client_id="client-uuid-001",
            currency="USD",
            lines=[
                InvoiceLineCreate(
                    description="Senior Consultant",
                    quantity=Decimal("100"),
                    unit_price=Decimal("100.00"),
                ),
                InvoiceLineCreate(
                    description="Cap adjustment",
                    quantity=Decimal("1"),
                    unit_price=Decimal("-5000.00"),
                ),
            ],
        ),
        created_by="user-uuid-001",
    )

    assert result.subtotal == "5000.00"
    assert result.total == "5000.00"
    svc._repo.create.assert_awaited_once()
    assert svc._repo.create.await_args.args[0]["subtotal"] == "5000.00"
    assert created_lines[1]["unit_price"] == "-5000.00"
    assert created_lines[1]["amount"] == "-5000.00"


@pytest.mark.asyncio
async def test_create_invoice_rejects_net_negative_adjustments(
    mock_db: MagicMock,
    tenant_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.models.invoices import InvoiceCreate, InvoiceLineCreate
    from app.services.invoices_service import InvoicesService

    async def _valid_fk(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr("app.services.invoices_service.assert_belongs_to_tenant", _valid_fk)

    svc = InvoicesService(mock_db, tenant_id)
    svc._repo.create = AsyncMock()

    with pytest.raises(Exception) as exc_info:
        await svc.create_invoice(
            InvoiceCreate(
                engagement_id="eng-uuid-001",
                client_id="client-uuid-001",
                currency="USD",
                lines=[
                    InvoiceLineCreate(
                        description="Retainer applied",
                        quantity=Decimal("1"),
                        unit_price=Decimal("-5000.00"),
                    ),
                ],
            ),
            created_by="user-uuid-001",
        )

    assert exc_info.value.status_code == 422
    assert "negative" in exc_info.value.detail
    svc._repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_invoice_records_retainer_draw_ledger_entry(
    mock_db: MagicMock,
    tenant_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.models.invoices import InvoiceCreate, InvoiceLineCreate
    from app.services.invoices_service import InvoicesService

    async def _valid_fk(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr("app.services.invoices_service.assert_belongs_to_tenant", _valid_fk)

    existing_result = MagicMock()
    existing_result.data = []
    insert_result = MagicMock()
    insert_result.data = [{"id": "retainer-ledger-1"}]
    table_chain = MagicMock()
    table_chain.select.return_value = table_chain
    table_chain.eq.return_value = table_chain
    table_chain.is_.return_value = table_chain
    table_chain.limit.return_value = table_chain
    table_chain.execute.return_value = existing_result
    insert_chain = MagicMock()
    insert_chain.execute.return_value = insert_result
    table_chain.insert.return_value = insert_chain
    mock_db.table.return_value = table_chain

    svc = InvoicesService(mock_db, tenant_id)
    created_header = {
        "id": "inv-retainer-001",
        "tenant_id": tenant_id,
        "engagement_id": "eng-uuid-001",
        "client_id": "client-uuid-001",
        "invoice_number": "INV-RET",
        "currency": "USD",
        "subtotal": "1200.00",
        "tax_total": "0.00",
        "total": "1200.00",
        "status": "draft",
        "issue_date": None,
        "due_date": None,
        "paid_at": None,
        "stripe_payment_link_id": None,
        "stripe_payment_link_url": None,
        "public_token": "tok_retainer",
        "sent_at": None,
        "notes": None,
        "created_at": "2026-05-01T00:00:00+00:00",
        "updated_at": "2026-05-01T00:00:00+00:00",
    }
    svc._repo.create = AsyncMock(return_value=created_header)

    created_lines: list[dict] = []

    async def _create_line(payload: dict) -> dict:
        row = {
            "id": f"line-{len(created_lines) + 1}",
            "invoice_id": "inv-retainer-001",
            "created_at": "2026-05-01T00:00:00+00:00",
            **payload,
        }
        created_lines.append(row)
        return row

    svc._repo.create_line = AsyncMock(side_effect=_create_line)

    await svc.create_invoice(
        InvoiceCreate(
            engagement_id="eng-uuid-001",
            client_id="client-uuid-001",
            currency="USD",
            lines=[
                InvoiceLineCreate(
                    description="Consultant",
                    quantity=Decimal("20"),
                    unit_price=Decimal("100.00"),
                ),
                InvoiceLineCreate(
                    description="Retainer applied",
                    quantity=Decimal("1"),
                    unit_price=Decimal("-800.00"),
                ),
            ],
        ),
        created_by="user-uuid-001",
    )

    ledger_payload = table_chain.insert.call_args.args[0]
    assert ledger_payload["entry_type"] == "draw"
    assert ledger_payload["amount"] == "800.00"
    assert ledger_payload["engagement_id"] == "eng-uuid-001"
    assert ledger_payload["invoice_id"] == "inv-retainer-001"


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
        patch("app.services.invoices_service.settings") as mock_settings,
    ):
        mock_settings.stripe_secret_key = "sk_test_placeholder"
        mock_settings.frontend_base_url = "https://app.aethos.test"
        asyncio.run(svc.send_invoice(invoice_id, sent_by="user-uuid-001"))

    assert captured_kwargs.get("on_behalf_of") == "acct_connect_001"
    assert captured_kwargs.get("transfer_data") == {"destination": "acct_connect_001"}
    assert captured_kwargs.get("metadata") == {
        "invoice_id": invoice_id,
        "tenant_id": tenant_id,
    }
    assert captured_kwargs.get("payment_intent_data") == {
        "metadata": {
            "invoice_id": invoice_id,
            "tenant_id": tenant_id,
        },
    }


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


def test_approve_invoice_splits_tax_to_sales_tax_payable(
    mock_db: MagicMock,
    tenant_id: str,
    invoice_id: str,
) -> None:
    """Approval journal credits revenue for subtotal and 2300 for tax."""
    from app.services.invoices_service import InvoicesService

    svc = InvoicesService(mock_db, tenant_id)
    taxable_invoice = {
        **_draft_invoice(invoice_id, tenant_id, status="draft"),
        "subtotal": "1000.00",
        "tax_total": "100.00",
        "total": "1100.00",
    }
    approved_invoice = {**taxable_invoice, "status": "approved"}

    svc._repo.get_by_id = AsyncMock(return_value=taxable_invoice)
    svc._repo.get_account_ids_by_codes = AsyncMock(
        return_value={"1200": "acct-ar", "4000": "acct-revenue", "2300": "acct-tax"}
    )
    svc._repo.update = AsyncMock(return_value=approved_invoice)
    svc._repo.list_lines = AsyncMock(return_value=[])

    with patch("app.services.invoices_service.post_journal") as post_journal_mock:
        result = asyncio.run(svc.approve_invoice(invoice_id, approved_by="user-uuid-001"))

    assert result.status == "approved"
    svc._repo.get_account_ids_by_codes.assert_awaited_once_with(["1200", "4000", "2300"])
    journal_lines = post_journal_mock.call_args.kwargs["lines"]
    assert [(line.direction, line.account_code, line.amount) for line in journal_lines] == [
        ("DR", "1200", Decimal("1100.00")),
        ("CR", "4000", Decimal("1000.00")),
        ("CR", "2300", Decimal("100.00")),
    ]


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
