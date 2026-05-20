"""Repository for invoices and invoice_lines.

All queries are tenant-scoped.  The caller must set `app.current_tenant_id`
before any query (handled by TenantMiddleware + get_anon_client).
"""
# Prahari review required — see docs/team/SECURITY_REVIEW.md

from __future__ import annotations

import asyncio
import logging

from supabase import Client

logger = logging.getLogger(__name__)


class InvoicesRepository:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Invoices
    # ------------------------------------------------------------------

    async def list_invoices(
        self,
        engagement_id: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        def _list() -> list[dict]:
            q = (
                self.db.table("invoices")
                .select("*")
                .eq("tenant_id", self.tenant_id)
                .is_("deleted_at", "null")
                .order("created_at", desc=True)
            )
            if engagement_id:
                q = q.eq("engagement_id", engagement_id)
            if status:
                q = q.eq("status", status)
            return q.execute().data or []

        return await asyncio.to_thread(_list)

    async def get_by_id(self, invoice_id: str) -> dict | None:
        def _get() -> dict | None:
            result = (
                self.db.table("invoices")
                .select("*")
                .eq("id", invoice_id)
                .eq("tenant_id", self.tenant_id)
                .is_("deleted_at", "null")
                .execute()
            )
            return result.data[0] if result.data else None

        return await asyncio.to_thread(_get)

    async def get_by_public_token(self, token: str) -> dict | None:
        """Fetch an invoice by its public_token — used on the unauthenticated payment page."""

        def _get() -> dict | None:
            result = (
                self.db.table("invoices")
                .select("*")
                .eq("public_token", token)
                .is_("deleted_at", "null")
                .execute()
            )
            return result.data[0] if result.data else None

        return await asyncio.to_thread(_get)

    async def create(self, data: dict) -> dict:
        def _create() -> dict:
            result = self.db.table("invoices").insert(data).execute()
            if not result.data:
                raise RuntimeError("Invoice insert returned no data")
            return result.data[0]

        return await asyncio.to_thread(_create)

    async def update(self, invoice_id: str, data: dict) -> dict | None:
        def _update() -> dict | None:
            result = (
                self.db.table("invoices")
                .update(data)
                .eq("id", invoice_id)
                .eq("tenant_id", self.tenant_id)
                .execute()
            )
            return result.data[0] if result.data else None

        return await asyncio.to_thread(_update)

    # ------------------------------------------------------------------
    # Invoice lines
    # ------------------------------------------------------------------

    async def list_lines(self, invoice_id: str) -> list[dict]:
        def _list() -> list[dict]:
            return (
                self.db.table("invoice_lines")
                .select("*")
                .eq("invoice_id", invoice_id)
                .eq("tenant_id", self.tenant_id)
                .order("created_at")
                .execute()
                .data
                or []
            )

        return await asyncio.to_thread(_list)

    async def create_line(self, data: dict) -> dict:
        def _create() -> dict:
            result = self.db.table("invoice_lines").insert(data).execute()
            if not result.data:
                raise RuntimeError("Invoice line insert returned no data")
            return result.data[0]

        return await asyncio.to_thread(_create)

    # ------------------------------------------------------------------
    # Account lookup (for journal posting)
    # ------------------------------------------------------------------

    async def get_account_ids_by_codes(self, codes: list[str]) -> dict[str, str]:
        """Return {code: account_id} for the given COA codes in this tenant."""

        def _get() -> dict[str, str]:
            result = (
                self.db.table("accounts")
                .select("id, code")
                .eq("tenant_id", self.tenant_id)
                .in_("code", codes)
                .execute()
            )
            return {r["code"]: r["id"] for r in (result.data or [])}

        return await asyncio.to_thread(_get)

    # ------------------------------------------------------------------
    # Tenant lookup (for Connect check)
    # ------------------------------------------------------------------

    async def get_tenant(self) -> dict | None:
        def _get() -> dict | None:
            result = (
                self.db.table("tenants")
                .select(
                    "id, name, stripe_connect_account_id, stripe_connect_status, "
                    "stripe_connect_charges_enabled, stripe_connect_payouts_enabled"
                )
                .eq("id", self.tenant_id)
                .execute()
            )
            return result.data[0] if result.data else None

        return await asyncio.to_thread(_get)
