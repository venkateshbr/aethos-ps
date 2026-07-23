"""Unit tests for the Stripe webhook event-mode guard (#371 AC 1)."""

from __future__ import annotations

import pytest

from app.api.v1.endpoints.webhooks import event_mode_matches

pytestmark = pytest.mark.unit


def test_live_env_accepts_only_livemode_events() -> None:
    assert event_mode_matches("sk_live_abc", True) is True
    assert event_mode_matches("sk_live_abc", False) is False  # test event in live env
    assert event_mode_matches("sk_live_abc", None) is False


def test_test_env_accepts_only_test_events() -> None:
    assert event_mode_matches("sk_test_abc", False) is True
    assert event_mode_matches("sk_test_abc", None) is True   # unset treated as test
    assert event_mode_matches("sk_test_abc", True) is False  # live event in test env


def test_unknown_or_unconfigured_key_cannot_be_checked_so_passes() -> None:
    # Signature verification (mode-specific secret) remains the gate here.
    assert event_mode_matches("", True) is True
    assert event_mode_matches("rk_live_restricted", False) is True
