"""Repository for invoices and invoice_lines.

All queries are tenant-scoped.  The caller must set `app.current_tenant_id`
before any query (handled by TenantMiddleware + get_anon_client).
"""
# Prahari review required — see docs/team/SECURITY_REVIEW.md

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from supabase import Client

logger = logging.getLogger(__name__)


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
    except (TypeError, ValueError):
        return False
    return True


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
                # Embed client.name so the Invoices list table can render it
                # without an N+1 per-row lookup. PostgREST returns the nested
                # object under the relation name "clients".
                .select("*, clients(name)")
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
        if not _is_uuid(invoice_id):
            return None

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

    async def get_revoked_public_token(self, token: str) -> dict | None:
        """Return a revoked public invoice token row, if the token was retired."""

        def _get() -> dict | None:
            result = (
                self.db.table("invoice_public_token_revocations")
                .select("*")
                .eq("public_token", token)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None

        return await asyncio.to_thread(_get)

    async def revoke_public_token(
        self,
        *,
        invoice: dict,
        public_token: str,
        revoked_by: str,
        reason: str = "rotated",
    ) -> dict:
        """Persist a retired public token before the invoice token is rotated."""

        def _insert() -> dict:
            result = (
                self.db.table("invoice_public_token_revocations")
                .insert(
                    {
                        "tenant_id": invoice["tenant_id"],
                        "invoice_id": invoice["id"],
                        "public_token": public_token,
                        "revoked_by": revoked_by,
                        "reason": reason,
                    }
                )
                .execute()
            )
            if not result.data:
                raise RuntimeError("Invoice public token revocation insert returned no data")
            return result.data[0]

        return await asyncio.to_thread(_insert)

    async def create(self, data: dict) -> dict:
        def _create() -> dict:
            result = self.db.table("invoices").insert(data).execute()
            if not result.data:
                raise RuntimeError("Invoice insert returned no data")
            return result.data[0]

        return await asyncio.to_thread(_create)

    async def update(self, invoice_id: str, data: dict) -> dict | None:
        if not _is_uuid(invoice_id):
            return None

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
        if not _is_uuid(invoice_id):
            return []

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

    async def get_tax_rate(self, tax_rate_id: str) -> dict | None:
        """Return an active system or tenant tax rate visible to this tenant."""
        if not _is_uuid(tax_rate_id):
            return None

        def _get() -> dict | None:
            result = (
                self.db.table("tax_rates")
                .select("id, tenant_id, rate, is_active")
                .eq("id", tax_rate_id)
                .is_("deleted_at", "null")
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if not rows:
                return None
            row = rows[0]
            row_tenant = row.get("tenant_id")
            if row_tenant is not None and str(row_tenant) != self.tenant_id:
                return None
            if not bool(row.get("is_active", True)):
                return None
            return row

        return await asyncio.to_thread(_get)

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
