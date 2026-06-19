"""Tenant self-management endpoint.

DELETE /api/v1/tenants  — owner-only; requires X-Confirm-Delete: true header.
Cancels Stripe subscription (if active) then soft-deletes the tenant.
"""

from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.auth import CurrentUser
from app.core.config import settings
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    x_confirm_delete: str | None = Header(default=None, alias="X-Confirm-Delete"),
    current_user: CurrentUser = require_role(UserRole.owner),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> None:
    """Delete this tenant account.

    - Requires header ``X-Confirm-Delete: true``
    - Requires owner role
    - Cancels Stripe subscription if present
    - Soft-deletes the tenant by setting ``status = 'deleted'``
    """
    if x_confirm_delete != "true":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required header: X-Confirm-Delete: true",
        )

    # Fetch tenant to get Stripe subscription ID
    tenant_result = (
        db.table("tenants")
        .select("id, status, stripe_subscription_id")
        .eq("id", tenant_id)
        .execute()
    )
    if not tenant_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    tenant = tenant_result.data[0]
    if tenant.get("status") == "deleted":
        return  # Already deleted — idempotent

    # Cancel Stripe subscription
    stripe_sub_id: str | None = tenant.get("stripe_subscription_id")
    if stripe_sub_id and settings.stripe_secret_key:
        try:
            stripe.api_key = settings.stripe_secret_key
            stripe.Subscription.cancel(stripe_sub_id)
            logger.info(
                "tenants: cancelled Stripe subscription %s for tenant %s",
                stripe_sub_id,
                tenant_id,
            )
        except stripe.StripeError as exc:
            # Log and continue — the tenant record should still be deleted
            logger.error(
                "tenants: failed to cancel Stripe subscription %s: %s",
                stripe_sub_id,
                exc,
                extra={"tenant_id": tenant_id},
            )

    # Soft-delete
    db.table("tenants").update(
        {"status": "deleted", "stripe_subscription_status": "canceled"}
    ).eq("id", tenant_id).execute()

    logger.info("tenants: soft-deleted tenant %s by user %s", tenant_id, current_user.user_id)
