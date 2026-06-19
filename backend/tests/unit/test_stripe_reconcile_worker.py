"""Unit tests for the Stripe reconcile worker (#180).

Tests:
- Skips when stripe_secret_key is not configured
- Skips invoices with no payment link
- Marks invoice paid when Stripe session found with payment_status=paid
- Handles Stripe errors per-invoice without crashing
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from procrastinate.tasks import Task

pytestmark = pytest.mark.unit


def _make_db_mock(invoices: list[dict]) -> MagicMock:
    db = MagicMock()
    result_mock = MagicMock()
    result_mock.data = invoices

    update_mock = MagicMock()
    update_mock.eq.return_value = update_mock
    update_mock.execute.return_value = MagicMock()

    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.lt.return_value = table_mock
    table_mock.is_.return_value = table_mock
    table_mock.execute.return_value = result_mock
    table_mock.update.return_value = update_mock

    db.table.return_value = table_mock
    return db


# ---------------------------------------------------------------------------
# Test 1: task is registered correctly
# ---------------------------------------------------------------------------


def test_reconcile_task_is_registered() -> None:
    from app.workers.stripe_reconcile_worker import reconcile_sent_invoices

    assert isinstance(reconcile_sent_invoices, Task)


# ---------------------------------------------------------------------------
# Test 2: skips when stripe_secret_key not configured
# ---------------------------------------------------------------------------


def test_skips_when_stripe_not_configured() -> None:
    from app.workers.stripe_reconcile_worker import reconcile_sent_invoices

    with (
        patch("app.workers.stripe_reconcile_worker.settings") as mock_settings,
        patch("app.workers.stripe_reconcile_worker.get_service_role_client") as mock_db_fn,
    ):
        mock_settings.stripe_secret_key = ""
        result = reconcile_sent_invoices("tenant-001")

    assert result == {"reconciled": 0, "skipped": 0, "errors": 0}
    mock_db_fn.assert_not_called()


# ---------------------------------------------------------------------------
# Test 3: skips invoice with no payment link
# ---------------------------------------------------------------------------


def test_skips_invoice_without_payment_link() -> None:
    from app.workers.stripe_reconcile_worker import reconcile_sent_invoices

    invoice_without_link = {
        "id": "inv-no-link",
        "invoice_number": "INV-001",
        "stripe_payment_link_id": None,
    }
    db = _make_db_mock([invoice_without_link])

    with (
        patch("app.workers.stripe_reconcile_worker.settings") as mock_settings,
        patch("app.workers.stripe_reconcile_worker.get_service_role_client", return_value=db),
        patch("app.workers.stripe_reconcile_worker.stripe"),
    ):
        mock_settings.stripe_secret_key = "sk_test_placeholder"
        result = reconcile_sent_invoices("tenant-001")

    assert result["reconciled"] == 0
    assert result["skipped"] == 1
    assert result["errors"] == 0


# ---------------------------------------------------------------------------
# Test 4: reconciles invoice with paid Stripe session
# ---------------------------------------------------------------------------


def test_reconciles_paid_invoice() -> None:
    from app.workers.stripe_reconcile_worker import reconcile_sent_invoices

    invoice = {
        "id": "inv-paid",
        "invoice_number": "INV-002",
        "stripe_payment_link_id": "plink_abc",
    }
    db = _make_db_mock([invoice])

    paid_session = MagicMock()
    paid_session.payment_status = "paid"
    paid_session.id = "cs_test_001"

    sessions_mock = MagicMock()
    sessions_mock.auto_paging_iter.return_value = iter([paid_session])

    with (
        patch("app.workers.stripe_reconcile_worker.settings") as mock_settings,
        patch("app.workers.stripe_reconcile_worker.get_service_role_client", return_value=db),
        patch("app.workers.stripe_reconcile_worker.stripe") as mock_stripe,
    ):
        mock_settings.stripe_secret_key = "sk_test_placeholder"
        mock_stripe.checkout.Session.list.return_value = sessions_mock
        result = reconcile_sent_invoices("tenant-001")

    assert result["reconciled"] == 1
    assert result["skipped"] == 0
    assert result["errors"] == 0


# ---------------------------------------------------------------------------
# Test 5: handles Stripe error per invoice without crashing
# ---------------------------------------------------------------------------


def test_handles_stripe_error_gracefully() -> None:
    import stripe as stripe_lib

    from app.workers.stripe_reconcile_worker import reconcile_sent_invoices

    invoice = {
        "id": "inv-err",
        "invoice_number": "INV-003",
        "stripe_payment_link_id": "plink_xyz",
    }
    db = _make_db_mock([invoice])

    with (
        patch("app.workers.stripe_reconcile_worker.settings") as mock_settings,
        patch("app.workers.stripe_reconcile_worker.get_service_role_client", return_value=db),
        patch("app.workers.stripe_reconcile_worker.stripe") as mock_stripe,
    ):
        mock_settings.stripe_secret_key = "sk_test_placeholder"
        mock_stripe.StripeError = stripe_lib.StripeError
        mock_stripe.checkout.Session.list.side_effect = stripe_lib.StripeError("network error")
        result = reconcile_sent_invoices("tenant-001")

    assert result["errors"] == 1
    assert result["reconciled"] == 0
