"""Billing-access policy regression tests for expired trials (#481)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.auth import CurrentUser
from app.core.tenant import get_tenant_id

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


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, table: str) -> None:
        self.table = table

    def select(self, _columns: str) -> _Query:
        return self

    def eq(self, _key: str, _value: Any) -> _Query:
        return self

    def is_(self, _key: str, _value: Any) -> _Query:
        return self

    def limit(self, _value: int) -> _Query:
        return self

    def execute(self) -> _Result:
        if self.table == "tenant_users":
            return _Result([{"id": "membership-1", "role": "owner"}])
        if self.table == "tenants":
            return _Result(
                [
                    {
                        "stripe_subscription_status": "trialing",
                        "trial_ends_at": "2020-01-01T00:00:00Z",
                        "billing_access_override_until": None,
                    }
                ]
            )
        raise AssertionError(self.table)


class _Db:
    def table(self, name: str) -> _Query:
        return _Query(name)


def _request(method: str, path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [(b"x-tenant-id", b"11111111-1111-1111-1111-111111111111")],
        }
    )


def test_expired_trial_blocks_erp_mutations_with_billing_error() -> None:
    """Authenticated membership does not bypass expired-trial read-only mode."""
    with pytest.raises(HTTPException) as exc:
        get_tenant_id(
            _request("POST", "/api/v1/invoices"),
            CurrentUser(user_id="user-1", email="owner@example.com", role="authenticated"),
            _Db(),  # type: ignore[arg-type]
        )

    assert exc.value.status_code == 402
    assert exc.value.detail == {
        "code": "SUBSCRIPTION_REQUIRED",
        "message": "This workspace is read-only. Manage billing to restore changes.",
    }


def test_active_override_restores_full_access_until_its_expiry() -> None:
    from app.services.billing.access_policy import evaluate_billing_access

    access = evaluate_billing_access(
        provider_status="trialing",
        trial_ends_at="2020-01-01T00:00:00Z",
        override_until="2026-09-01T00:00:00Z",
        as_of=datetime(2026, 8, 6, tzinfo=UTC),
    )

    assert access.effective_status == "override_active"
    assert access.access_mode == "full"


def test_scheduled_work_excludes_expired_trials() -> None:
    from app.services.billing.access_policy import filter_tenants_with_write_access

    tenants = [
        {
            "id": "expired",
            "stripe_subscription_status": "trialing",
            "trial_ends_at": "2020-01-01T00:00:00Z",
            "billing_access_override_until": None,
        },
        {
            "id": "paid",
            "stripe_subscription_status": "active",
            "trial_ends_at": None,
            "billing_access_override_until": None,
        },
    ]

    assert [row["id"] for row in filter_tenants_with_write_access(tenants)] == ["paid"]
