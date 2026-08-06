"""Billing-access policy regression tests for expired trials (#481)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.unit


def test_trial_past_reconciliation_grace_is_read_only() -> None:
    """A stale trial cannot retain mutation access indefinitely."""
    from app.services.billing.access_policy import evaluate_billing_access

    access = evaluate_billing_access(
        provider_status="trialing",
        trial_ends_at="2026-08-03T14:43:50Z",
        override_until=None,
        as_of=datetime(2026, 8, 4, 14, 43, 51, tzinfo=UTC),
    )

    assert access.effective_status == "trial_expired"
    assert access.access_mode == "read_only"
    assert access.action == "manage_billing"
