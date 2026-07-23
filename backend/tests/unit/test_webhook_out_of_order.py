"""#371 AC 4 — Stripe subscription webhooks reject out-of-order events."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.api.v1.endpoints.webhooks import _is_stale_subscription_event

pytestmark = pytest.mark.unit


def _event(created: int) -> SimpleNamespace:
    return SimpleNamespace(created=created, id="evt_1")


def test_older_event_than_last_applied_is_stale() -> None:
    tenant = {"id": "t1", "stripe_subscription_event_at": 2000}
    assert _is_stale_subscription_event(tenant, _event(1000)) is True


def test_newer_event_is_not_stale() -> None:
    tenant = {"id": "t1", "stripe_subscription_event_at": 2000}
    assert _is_stale_subscription_event(tenant, _event(3000)) is False


def test_equal_timestamp_is_not_stale() -> None:
    # Idempotency (event_id) handles exact duplicates; equal ts is not "older".
    tenant = {"id": "t1", "stripe_subscription_event_at": 2000}
    assert _is_stale_subscription_event(tenant, _event(2000)) is False


def test_first_event_with_no_prior_timestamp_is_not_stale() -> None:
    assert _is_stale_subscription_event({"id": "t1"}, _event(1000)) is False
    assert _is_stale_subscription_event({"id": "t1", "stripe_subscription_event_at": None}, _event(1000)) is False
