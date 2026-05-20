"""Stripe Connect Standard onboarding router.

Issue #51: Stripe Connect Standard onboarding + account.updated webhook

Routes (owner only):
  GET /stripe/connect/oauth-url   — returns the Stripe OAuth URL to begin onboarding
  GET /stripe/connect/return      — OAuth callback: exchange code → store account ID
  GET /stripe/connect/status      — returns current Connect status for this tenant
"""
# Prahari review required — see docs/team/SECURITY_REVIEW.md

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser
from app.core.config import settings
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.domain.exceptions import BillingError
from app.models.invoices import ConnectOAuthUrlResponse, ConnectStatusResponse
from app.repositories.invoices_repo import InvoicesRepository
from app.repositories.tenant_repo import TenantRepository
from app.services.billing.stripe_service import StripeService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


def _stripe_svc() -> StripeService:
    return StripeService(settings)


# ---------------------------------------------------------------------------
# GET /oauth-url — generate OAuth URL (owner only)
# ---------------------------------------------------------------------------


@router.get("/oauth-url", response_model=ConnectOAuthUrlResponse)
async def get_oauth_url(
    country: str = Query(default="US", min_length=2, max_length=2, description="ISO 2-letter country"),
    current_user: CurrentUser = require_role(UserRole.owner),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    stripe_svc: StripeService = Depends(_stripe_svc),  # noqa: B008
) -> ConnectOAuthUrlResponse:
    """Return the Stripe Connect OAuth URL for the tenant owner to begin onboarding.

    The ``redirect_uri`` is constructed from the backend's base URL — it must
    match a URI registered in the Stripe dashboard (Connect > Settings > Redirects).
    """
    redirect_uri = f"{settings.frontend_base_url}/settings/billing/connect/return"
    url = await stripe_svc.create_connect_oauth_url(
        tenant_id=tenant_id,
        redirect_uri=redirect_uri,
        country=country.upper(),
    )
    return ConnectOAuthUrlResponse(url=url)


# ---------------------------------------------------------------------------
# GET /return — OAuth callback (owner only)
# ---------------------------------------------------------------------------


@router.get("/return")
async def handle_connect_return(
    code: str = Query(..., description="OAuth authorization code from Stripe"),
    state: str = Query(..., description="Tenant ID embedded in state parameter"),
    current_user: CurrentUser = require_role(UserRole.owner),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
    stripe_svc: StripeService = Depends(_stripe_svc),  # noqa: B008
) -> dict:
    """Exchange OAuth code for Stripe Connect account ID and persist to tenant.

    Security: The ``state`` parameter must match the authenticated tenant_id to
    prevent CSRF on the Connect callback.
    """
    # CSRF check: state must match the authenticated tenant's ID
    if state != tenant_id:
        logger.warning(
            "Connect OAuth state mismatch — possible CSRF",
            extra={"state": state, "tenant_id": tenant_id},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state mismatch",
        )

    try:
        token_data = await stripe_svc.exchange_connect_code(code)
    except BillingError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe Connect error: {exc}",
        ) from exc

    connect_account_id = token_data["stripe_connect_account_id"]

    # Fetch account capabilities from Stripe
    try:
        account_info = await stripe_svc.get_connect_account(connect_account_id)
    except BillingError:
        # Not fatal — store the account ID and update capabilities on next webhook
        account_info = {"charges_enabled": False, "payouts_enabled": False}

    # Persist to tenant
    tenant_repo = TenantRepository(db)
    await tenant_repo.update_tenant(
        tenant_id,
        {
            "stripe_connect_account_id": connect_account_id,
            "stripe_connect_status": "active" if account_info["charges_enabled"] else "pending",
            "stripe_connect_charges_enabled": account_info["charges_enabled"],
            "stripe_connect_payouts_enabled": account_info["payouts_enabled"],
        },
    )

    logger.info(
        "Stripe Connect account linked",
        extra={
            "tenant_id": tenant_id,
            "connect_account_id": connect_account_id,
            "charges_enabled": account_info["charges_enabled"],
        },
    )

    return {
        "status": "connected",
        "stripe_connect_account_id": connect_account_id,
        "charges_enabled": account_info["charges_enabled"],
        "payouts_enabled": account_info["payouts_enabled"],
    }


# ---------------------------------------------------------------------------
# GET /status — return current Connect status (owner only)
# ---------------------------------------------------------------------------


@router.get("/status", response_model=ConnectStatusResponse)
async def get_connect_status(
    current_user: CurrentUser = require_role(UserRole.owner),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> ConnectStatusResponse:
    """Return the current Stripe Connect status for this tenant."""
    repo = InvoicesRepository(db, tenant_id)
    tenant = await repo.get_tenant()

    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return ConnectStatusResponse(
        status=tenant.get("stripe_connect_status", "not_connected"),
        charges_enabled=bool(tenant.get("stripe_connect_charges_enabled", False)),
        payouts_enabled=bool(tenant.get("stripe_connect_payouts_enabled", False)),
        stripe_connect_account_id=tenant.get("stripe_connect_account_id"),
    )
