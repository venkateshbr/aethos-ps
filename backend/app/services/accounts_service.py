"""Chart-of-accounts read service."""

from __future__ import annotations

import asyncio
import logging

from app.models.accounts import AccountResponse, AccountType
from supabase import Client

logger = logging.getLogger(__name__)


class AccountsService:
    """Tenant-scoped chart-of-accounts queries."""

    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    async def list_accounts(
        self,
        *,
        account_type: AccountType | None = None,
        search: str | None = None,
        limit: int | None = None,
    ) -> list[AccountResponse]:
        """Return active accounts for this tenant, sorted by account code."""

        def _fetch() -> list[dict]:
            query = (
                self.db.table("accounts")
                .select("id, code, name, account_type, is_system, parent_id")
                .eq("tenant_id", self.tenant_id)
                .is_("deleted_at", "null")
                .order("code")
            )
            if account_type is not None:
                query = query.eq("account_type", account_type)
            return query.execute().data or []

        rows = await asyncio.to_thread(_fetch)
        if search:
            needle = search.strip().lower()
            rows = [
                row
                for row in rows
                if needle in str(row.get("code") or "").lower()
                or needle in str(row.get("name") or "").lower()
                or needle in str(row.get("account_type") or "").lower()
            ]
        if limit is not None:
            rows = rows[:limit]
        return [
            AccountResponse(
                id=str(row["id"]),
                code=str(row["code"]),
                name=str(row["name"]),
                account_type=row["account_type"],
                is_system=bool(row["is_system"]),
                parent_id=str(row["parent_id"]) if row.get("parent_id") else None,
            )
            for row in rows
        ]
