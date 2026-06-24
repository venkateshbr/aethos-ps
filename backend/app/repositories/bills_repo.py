"""Repository: tenant-scoped data access for bills and bill_lines tables."""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal

from app.services.postgrest_errors import is_missing_column_error
from supabase import Client

logger = logging.getLogger(__name__)

_BILLS_TABLE = "bills"
_LINES_TABLE = "bill_lines"
_OPTIONAL_BILL_FIELDS = frozenset(
    {
        "purchase_order_id",
        "po_match_status",
        "po_match_summary",
        "source_document_id",
        "vendor_invoice_review",
    }
)
_OPTIONAL_BILL_LINE_FIELDS = frozenset(
    {"is_prepaid", "service_start_date", "service_end_date"}
)


class BillsRepository:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _base_query(self):  # type: ignore[no-untyped-def]
        return (
            self.db.table(_BILLS_TABLE)
            .select("*")
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
        )

    # ------------------------------------------------------------------
    # Read — bills
    # ------------------------------------------------------------------

    async def list(
        self,
        status: str | None = None,
        client_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        query = self._base_query().order("created_at", desc=True).limit(limit)
        if status:
            query = query.eq("status", status)
        if client_id:
            query = query.eq("client_id", client_id)
        result = await asyncio.to_thread(lambda: query.execute())
        return result.data or []

    async def get(self, bill_id: str) -> dict | None:
        result = await asyncio.to_thread(
            lambda: self._base_query().eq("id", bill_id).execute()
        )
        return result.data[0] if result.data else None

    async def get_lines(self, bill_id: str) -> list[dict]:
        result = await asyncio.to_thread(
            lambda: self.db.table(_LINES_TABLE)
            .select("*")
            .eq("bill_id", bill_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )
        return result.data or []

    # ------------------------------------------------------------------
    # Write — bills
    # ------------------------------------------------------------------

    async def create(self, data: dict) -> dict:
        payload = {**data, "tenant_id": self.tenant_id}
        try:
            result = await asyncio.to_thread(
                lambda: self.db.table(_BILLS_TABLE).insert(payload).execute()
            )
        except Exception as exc:
            if not is_missing_column_error(exc, _OPTIONAL_BILL_FIELDS):
                raise
            fallback_payload = _without_fields(payload, _OPTIONAL_BILL_FIELDS)
            if fallback_payload == payload:
                raise
            logger.warning(
                "bills table is missing optional PO match columns; retrying insert "
                "without those fields"
            )
            result = await asyncio.to_thread(
                lambda: self.db.table(_BILLS_TABLE).insert(fallback_payload).execute()
            )
        return result.data[0]

    async def update(self, bill_id: str, patch: dict) -> dict | None:
        existing = await self.get(bill_id)
        if existing is None:
            return None
        try:
            result = await asyncio.to_thread(
                lambda: self.db.table(_BILLS_TABLE)
                .update(patch)
                .eq("id", bill_id)
                .eq("tenant_id", self.tenant_id)
                .execute()
            )
        except Exception as exc:
            if not is_missing_column_error(exc, _OPTIONAL_BILL_FIELDS):
                raise
            fallback_patch = _without_fields(patch, _OPTIONAL_BILL_FIELDS)
            if fallback_patch == patch:
                raise
            if not fallback_patch:
                logger.warning(
                    "bills table is missing optional PO match columns; skipping "
                    "update because no supported fields remain"
                )
                return existing
            logger.warning(
                "bills table is missing optional PO match columns; retrying update "
                "without those fields"
            )
            result = await asyncio.to_thread(
                lambda: self.db.table(_BILLS_TABLE)
                .update(fallback_patch)
                .eq("id", bill_id)
                .eq("tenant_id", self.tenant_id)
                .execute()
            )
        return result.data[0] if result.data else None

    async def update_totals(
        self,
        bill_id: str,
        subtotal: Decimal,
        tax_total: Decimal,
        total: Decimal,
    ) -> None:
        await asyncio.to_thread(
            lambda: self.db.table(_BILLS_TABLE)
            .update(
                {
                    "subtotal": str(subtotal),
                    "tax_total": str(tax_total),
                    "total": str(total),
                }
            )
            .eq("id", bill_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )

    # ------------------------------------------------------------------
    # Write — bill lines
    # ------------------------------------------------------------------

    async def create_line(self, bill_id: str, data: dict) -> dict:
        payload = {**data, "bill_id": bill_id, "tenant_id": self.tenant_id}
        try:
            result = await asyncio.to_thread(
                lambda: self.db.table(_LINES_TABLE).insert(payload).execute()
            )
        except Exception as exc:
            if not is_missing_column_error(exc, _OPTIONAL_BILL_LINE_FIELDS):
                raise
            fallback_payload = _without_fields(payload, _OPTIONAL_BILL_LINE_FIELDS)
            if fallback_payload == payload:
                raise
            logger.warning(
                "bill_lines table is missing optional prepaid columns; retrying insert "
                "without those fields"
            )
            result = await asyncio.to_thread(
                lambda: self.db.table(_LINES_TABLE).insert(fallback_payload).execute()
            )
        return result.data[0]

    # ------------------------------------------------------------------
    # Aging — AP aging buckets
    # ------------------------------------------------------------------

    async def get_approved_overdue_bills(self) -> list[dict]:
        """Return approved bills with a due_date for aging calculation."""
        result = await asyncio.to_thread(
            lambda: self.db.table(_BILLS_TABLE)
            .select("id,total,due_date,currency")
            .eq("tenant_id", self.tenant_id)
            .in_("status", ["approved", "partially_paid"])
            .is_("deleted_at", "null")
            .execute()
        )
        return result.data or []

    # ------------------------------------------------------------------
    # Idempotency: find bill created from a given suggestion
    # ------------------------------------------------------------------

    async def find_by_suggestion(self, suggestion_id: str) -> dict | None:
        """Check if a bill already exists that was materialised from this suggestion.

        Bills materialised via the HITL inbox store the suggestion_id in their
        notes field as a fallback lookup (no dedicated FK in v1 schema).
        A dedicated reference column should be added in v1.1.
        """
        result = await asyncio.to_thread(
            lambda: self.db.table(_BILLS_TABLE)
            .select("*")
            .eq("tenant_id", self.tenant_id)
            .ilike("notes", f"%suggestion:{suggestion_id}%")
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    # ------------------------------------------------------------------
    # GL: lookup account id by code
    # ------------------------------------------------------------------

    async def get_account_id_by_code(self, code: str) -> str | None:
        result = await asyncio.to_thread(
            lambda: self.db.table("accounts")
            .select("id")
            .eq("tenant_id", self.tenant_id)
            .eq("code", code)
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
        return result.data[0]["id"] if result.data else None

    async def list_linked_to_purchase_order(self, purchase_order_id: str) -> list[dict]:
        result = await asyncio.to_thread(
            lambda: self.db.table(_BILLS_TABLE)
            .select("id,total,status")
            .eq("tenant_id", self.tenant_id)
            .eq("purchase_order_id", purchase_order_id)
            .is_("deleted_at", "null")
            .execute()
        )
        return result.data or []


def _without_fields(payload: dict, fields: frozenset[str]) -> dict:
    return {key: value for key, value in payload.items() if key not in fields}
