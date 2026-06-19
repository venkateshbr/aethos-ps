"""Unit tests for the delete tenant endpoint (#197).

Tests:
- Returns 400 if X-Confirm-Delete header is missing
- Returns 204 and calls Stripe cancel when subscription exists
- Soft-deletes the tenant (status = 'deleted')
- Idempotent: 204 if already deleted
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _make_current_user(user_id: str = "user-owner-001") -> MagicMock:
    user = MagicMock()
    user.user_id = user_id
    user.email = "owner@example.com"
    return user


def test_delete_tenant_missing_header_returns_400() -> None:
    """DELETE /tenants without X-Confirm-Delete: true returns 400."""
    from fastapi import HTTPException

    from app.api.v1.endpoints.tenants import delete_tenant

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            delete_tenant(
                x_confirm_delete=None,
                current_user=_make_current_user(),
                tenant_id="tenant-001",
                db=MagicMock(),
            )
        )
    assert exc_info.value.status_code == 400


def test_delete_tenant_wrong_header_value_returns_400() -> None:
    from fastapi import HTTPException

    from app.api.v1.endpoints.tenants import delete_tenant

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            delete_tenant(
                x_confirm_delete="yes",
                current_user=_make_current_user(),
                tenant_id="tenant-001",
                db=MagicMock(),
            )
        )
    assert exc_info.value.status_code == 400


def test_delete_tenant_soft_deletes_and_cancels_stripe() -> None:
    """Successful delete marks tenant deleted and cancels Stripe subscription."""
    from app.api.v1.endpoints.tenants import delete_tenant

    db = MagicMock()

    tenant_result = MagicMock()
    tenant_result.data = [
        {
            "id": "tenant-001",
            "status": "active",
            "stripe_subscription_id": "sub_test_001",
        }
    ]

    update_mock = MagicMock()
    update_mock.eq.return_value = update_mock
    update_mock.execute.return_value = MagicMock()

    db.table.return_value.select.return_value.eq.return_value.execute.return_value = tenant_result
    db.table.return_value.update.return_value = update_mock

    with (
        patch("app.api.v1.endpoints.tenants.settings") as mock_settings,
        patch("app.api.v1.endpoints.tenants.stripe") as mock_stripe,
    ):
        mock_settings.stripe_secret_key = "sk_test_placeholder"
        asyncio.run(
            delete_tenant(
                x_confirm_delete="true",
                current_user=_make_current_user(),
                tenant_id="tenant-001",
                db=db,
            )
        )

    # Stripe subscription should have been cancelled
    mock_stripe.Subscription.cancel.assert_called_once_with("sub_test_001")

    # Tenant should be soft-deleted
    db.table.return_value.update.assert_called_once_with(
        {"status": "deleted", "stripe_subscription_status": "canceled"}
    )


def test_delete_tenant_idempotent_when_already_deleted() -> None:
    """Deleting an already-deleted tenant returns 204 without calling Stripe."""
    from app.api.v1.endpoints.tenants import delete_tenant

    db = MagicMock()

    tenant_result = MagicMock()
    tenant_result.data = [
        {
            "id": "tenant-001",
            "status": "deleted",
            "stripe_subscription_id": None,
        }
    ]

    db.table.return_value.select.return_value.eq.return_value.execute.return_value = tenant_result

    with patch("app.api.v1.endpoints.tenants.stripe") as mock_stripe:
        asyncio.run(
            delete_tenant(
                x_confirm_delete="true",
                current_user=_make_current_user(),
                tenant_id="tenant-001",
                db=db,
            )
        )

    mock_stripe.Subscription.cancel.assert_not_called()
