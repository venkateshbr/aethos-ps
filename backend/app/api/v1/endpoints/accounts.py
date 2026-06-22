"""Chart-of-accounts endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_user_rls_client
from app.core.tenant import get_tenant_id
from app.models.accounts import AccountResponse, AccountType
from app.services.accounts_service import AccountsService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()

ACCOUNT_TYPE_QUERY = Query(
    None,
    description="Optional account type filter: asset, liability, equity, revenue, expense",
)
ACCOUNT_SEARCH_QUERY = Query(None, description="Optional search across account code, name, and type")
ACCOUNT_LIMIT_QUERY = Query(None, ge=1, le=500, description="Maximum accounts to return")


@router.get("", response_model=list[AccountResponse])
async def list_accounts(
    account_type: AccountType | None = ACCOUNT_TYPE_QUERY,
    search: str | None = ACCOUNT_SEARCH_QUERY,
    limit: int | None = ACCOUNT_LIMIT_QUERY,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_user_rls_client),  # noqa: B008
) -> list[AccountResponse]:
    """List active chart-of-accounts rows for the authenticated tenant."""
    svc = AccountsService(db=db, tenant_id=tenant_id)
    try:
        return await svc.list_accounts(account_type=account_type, search=search, limit=limit)
    except Exception as exc:
        logger.exception("Failed to list accounts for tenant %s", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        ) from exc
