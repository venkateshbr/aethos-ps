"""#493 — a failed Stripe handler must not be acknowledged.

Before this fix `_dispatch` was wrapped in a bare `except Exception:` that only
logged; the event was then written to the idempotency log and the endpoint
returned 200. Stripe never retried, and the redelivery guard skipped the event,
so a `checkout.session.completed` whose payment/journal write failed left cash
collected and nothing in the ledger.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import webhooks

pytestmark = pytest.mark.unit


class _FakeRepo:
    """Records what the endpoint wrote, and what it read for idempotency."""

    def __init__(self, existing: dict | None = None) -> None:
        self.existing = existing
        self.recorded: list[dict] = []

    async def get_webhook_event(self, provider_event_id: str) -> dict | None:
        return self.existing

    async def record_webhook_event(self, **kwargs) -> None:
        self.recorded.append(kwargs)

    async def get_by_stripe_customer(self, stripe_customer_id: str) -> dict | None:
        return None


class _FakeRequest:
    def __init__(self) -> None:
        self.headers = {"stripe-signature": "sig"}

    async def body(self) -> bytes:
        return b"{}"


class _FakeStripeService:
    def __init__(self, event) -> None:
        self._event = event

    async def construct_webhook_event(self, payload: bytes, sig_header: str):
        return self._event


def _event(event_id: str = "evt_1", event_type: str = "checkout.session.completed"):
    return SimpleNamespace(
        id=event_id,
        type=event_type,
        livemode=False,
        created=1000,
        data=SimpleNamespace(object={}),
    )


@pytest.fixture
def _no_livemode_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webhooks, "event_mode_matches", lambda secret_key, livemode: True)
    monkeypatch.setattr(webhooks, "_extract_customer_id", lambda event: None)
    monkeypatch.setattr(webhooks, "_extract_tenant_id", lambda event: "tenant-1")


async def test_handler_failure_returns_500_and_records_failed(
    monkeypatch: pytest.MonkeyPatch, _no_livemode_check: None
) -> None:
    repo = _FakeRepo(existing=None)
    monkeypatch.setattr(webhooks, "TenantRepository", lambda db: repo)

    async def _boom(event, tenant_repo, db):
        raise RuntimeError("journal post failed")

    monkeypatch.setattr(webhooks, "_dispatch", _boom)

    with pytest.raises(HTTPException) as excinfo:
        await webhooks.stripe_webhook(
            request=_FakeRequest(),
            db=object(),
            stripe_svc=_FakeStripeService(_event()),
        )

    assert excinfo.value.status_code == 500
    assert "journal post failed" not in str(excinfo.value.detail)
    assert len(repo.recorded) == 1
    assert repo.recorded[0]["processing_status"] == "failed"
    assert repo.recorded[0]["error_class"] == "RuntimeError"
    assert repo.recorded[0]["attempts"] == 1


async def test_successful_handler_records_processed(
    monkeypatch: pytest.MonkeyPatch, _no_livemode_check: None
) -> None:
    repo = _FakeRepo(existing=None)
    monkeypatch.setattr(webhooks, "TenantRepository", lambda db: repo)

    async def _ok(event, tenant_repo, db):
        return None

    monkeypatch.setattr(webhooks, "_dispatch", _ok)

    result = await webhooks.stripe_webhook(
        request=_FakeRequest(),
        db=object(),
        stripe_svc=_FakeStripeService(_event()),
    )

    assert result == {"received": True}
    assert repo.recorded[0]["processing_status"] == "processed"


async def test_previously_failed_event_is_reprocessed_on_redelivery(
    monkeypatch: pytest.MonkeyPatch, _no_livemode_check: None
) -> None:
    repo = _FakeRepo(existing={"processing_status": "failed", "attempts": 1})
    monkeypatch.setattr(webhooks, "TenantRepository", lambda db: repo)
    dispatched: list[bool] = []

    async def _ok(event, tenant_repo, db):
        dispatched.append(True)

    monkeypatch.setattr(webhooks, "_dispatch", _ok)

    result = await webhooks.stripe_webhook(
        request=_FakeRequest(),
        db=object(),
        stripe_svc=_FakeStripeService(_event()),
    )

    assert dispatched == [True], "a failed delivery must be retried, not skipped"
    assert result == {"received": True}
    assert repo.recorded[0]["processing_status"] == "processed"
    assert repo.recorded[0]["attempts"] == 2


async def test_already_processed_event_is_skipped(
    monkeypatch: pytest.MonkeyPatch, _no_livemode_check: None
) -> None:
    repo = _FakeRepo(existing={"processing_status": "processed", "attempts": 1})
    monkeypatch.setattr(webhooks, "TenantRepository", lambda db: repo)
    dispatched: list[bool] = []

    async def _ok(event, tenant_repo, db):
        dispatched.append(True)

    monkeypatch.setattr(webhooks, "_dispatch", _ok)

    result = await webhooks.stripe_webhook(
        request=_FakeRequest(),
        db=object(),
        stripe_svc=_FakeStripeService(_event()),
    )

    assert dispatched == [], "a processed delivery must stay idempotent"
    assert result == {"received": True}
    assert repo.recorded == []
