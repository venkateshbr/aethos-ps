"""Unit tests for FX gain/loss service (#191).

Tests:
- compute_fx_delta returns correct signed delta
- Immaterial deltas (< 0.01) return None / skip journal
- gain path: DR 1200 AR / CR 7100 FX Gain
- loss path: DR 7200 FX Loss / CR 1200 AR
- Same-currency invoices are skipped
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# compute_fx_delta
# ---------------------------------------------------------------------------


def test_compute_fx_delta_gain() -> None:
    from app.services.fx_gain_loss_service import compute_fx_delta

    delta = compute_fx_delta(Decimal("1010.00"), Decimal("1000.00"))
    assert delta == Decimal("10.00")


def test_compute_fx_delta_loss() -> None:
    from app.services.fx_gain_loss_service import compute_fx_delta

    delta = compute_fx_delta(Decimal("990.00"), Decimal("1000.00"))
    assert delta == Decimal("-10.00")


def test_compute_fx_delta_immaterial_rounds_to_zero() -> None:
    """0.005 rounds DOWN to 0.00 (HALF_DOWN) — immaterial, no journal needed."""
    from app.services.fx_gain_loss_service import compute_fx_delta

    delta = compute_fx_delta(Decimal("1000.005"), Decimal("1000.00"))
    assert delta == Decimal("0.00")


def test_compute_fx_delta_just_above_immaterial() -> None:
    from app.services.fx_gain_loss_service import compute_fx_delta

    delta = compute_fx_delta(Decimal("1000.01"), Decimal("1000.00"))
    assert delta == Decimal("0.01")


# ---------------------------------------------------------------------------
# post_fx_gain_loss_if_needed — same currency → skip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_same_currency_skipped() -> None:
    from app.services.fx_gain_loss_service import post_fx_gain_loss_if_needed

    db = MagicMock()
    invoice = {"id": "inv-001", "currency": "USD", "base_total": "1000.00"}
    result = await post_fx_gain_loss_if_needed(
        db=db,
        tenant_id="tenant-001",
        invoice=invoice,
        payment_amount=Decimal("1000.00"),
        payment_currency="USD",
    )
    assert result is None


# ---------------------------------------------------------------------------
# post_fx_gain_loss_if_needed — immaterial delta → skip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_immaterial_delta_skipped() -> None:
    from app.services.fx_gain_loss_service import post_fx_gain_loss_if_needed

    db = MagicMock()
    invoice = {"id": "inv-001", "currency": "GBP", "base_total": "1000.00"}
    result = await post_fx_gain_loss_if_needed(
        db=db,
        tenant_id="tenant-001",
        invoice=invoice,
        payment_amount=Decimal("1000.005"),
        payment_currency="USD",
    )
    assert result is None


# ---------------------------------------------------------------------------
# post_fx_gain_loss_if_needed — gain: posts journal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fx_gain_posts_journal() -> None:
    from app.services.fx_gain_loss_service import post_fx_gain_loss_if_needed

    db = MagicMock()

    # Mock _get_accounts
    mock_acct_result = MagicMock()
    mock_acct_result.data = [
        {"code": "1200", "id": "acct-ar"},
        {"code": "7100", "id": "acct-gain"},
    ]

    # Mock _system_actor
    mock_actor_result = MagicMock()
    mock_actor_result.data = [{"user_id": "user-system-001"}]

    def _build_chain(**kwargs: object) -> MagicMock:
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.in_.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        return chain

    table_mock = MagicMock()
    db.table.return_value = table_mock
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.in_.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.limit.return_value = table_mock

    call_count = 0

    def execute_side_effect() -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_acct_result  # accounts query
        return mock_actor_result  # actor query

    table_mock.execute.side_effect = execute_side_effect

    invoice = {
        "id": "inv-001",
        "invoice_number": "INV-0001",
        "currency": "GBP",
        "base_total": "990.00",
    }

    with patch("app.services.fx_gain_loss_service.post_journal") as mock_post:
        result = await post_fx_gain_loss_if_needed(
            db=db,
            tenant_id="tenant-001",
            invoice=invoice,
            payment_amount=Decimal("1000.00"),
            payment_currency="USD",
        )

    assert result == Decimal("10.00")
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["reference_type"] == "fx_gain_loss"
    # Gain: first line is DR 1200
    lines = call_kwargs["lines"]
    assert lines[0].direction == "DR"
    assert lines[0].account_code == "1200"
    assert lines[1].direction == "CR"
    assert lines[1].account_code == "7100"


# ---------------------------------------------------------------------------
# post_fx_gain_loss_if_needed — loss: posts journal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fx_loss_posts_journal() -> None:
    from app.services.fx_gain_loss_service import post_fx_gain_loss_if_needed

    db = MagicMock()

    mock_acct_result = MagicMock()
    mock_acct_result.data = [
        {"code": "1200", "id": "acct-ar"},
        {"code": "7200", "id": "acct-loss"},
    ]
    mock_actor_result = MagicMock()
    mock_actor_result.data = [{"user_id": "user-system-001"}]

    table_mock = MagicMock()
    db.table.return_value = table_mock
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.in_.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.limit.return_value = table_mock

    call_count = 0

    def execute_side_effect() -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_acct_result
        return mock_actor_result

    table_mock.execute.side_effect = execute_side_effect

    invoice = {
        "id": "inv-001",
        "invoice_number": "INV-0001",
        "currency": "GBP",
        "base_total": "1010.00",
    }

    with patch("app.services.fx_gain_loss_service.post_journal") as mock_post:
        result = await post_fx_gain_loss_if_needed(
            db=db,
            tenant_id="tenant-001",
            invoice=invoice,
            payment_amount=Decimal("1000.00"),
            payment_currency="USD",
        )

    assert result == Decimal("-10.00")
    mock_post.assert_called_once()
    lines = mock_post.call_args.kwargs["lines"]
    assert lines[0].direction == "DR"
    assert lines[0].account_code == "7200"
    assert lines[1].direction == "CR"
    assert lines[1].account_code == "1200"
