"""Repository for tenant-scoped procurement documents and lines."""

from __future__ import annotations

import asyncio
from decimal import Decimal

from supabase import Client

_DOCUMENTS_TABLE = "procurement_documents"
_LINES_TABLE = "procurement_document_lines"


class ProcurementRepository:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def _base_query(self):  # type: ignore[no-untyped-def]
        return (
            self.db.table(_DOCUMENTS_TABLE)
            .select("*")
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
        )

    async def list(
        self,
        *,
        document_type: str | None = None,
        status: str | None = None,
        client_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        query = self._base_query().order("created_at", desc=True).limit(limit)
        if document_type:
            query = query.eq("document_type", document_type)
        if status:
            query = query.eq("status", status)
        if client_id:
            query = query.eq("client_id", client_id)
        result = await asyncio.to_thread(lambda: query.execute())
        return result.data or []

    async def get(self, document_id: str) -> dict | None:
        result = await asyncio.to_thread(
            lambda: self._base_query().eq("id", document_id).execute()
        )
        return result.data[0] if result.data else None

    async def get_lines(self, document_id: str) -> list[dict]:
        result = await asyncio.to_thread(
            lambda: self.db.table(_LINES_TABLE)
            .select("*")
            .eq("procurement_document_id", document_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )
        return result.data or []

    async def create(self, data: dict) -> dict:
        payload = {**data, "tenant_id": self.tenant_id}
        result = await asyncio.to_thread(
            lambda: self.db.table(_DOCUMENTS_TABLE).insert(payload).execute()
        )
        return result.data[0]

    async def create_line(self, document_id: str, data: dict) -> dict:
        payload = {
            **data,
            "procurement_document_id": document_id,
            "tenant_id": self.tenant_id,
        }
        result = await asyncio.to_thread(
            lambda: self.db.table(_LINES_TABLE).insert(payload).execute()
        )
        return result.data[0]

    async def update(self, document_id: str, patch: dict) -> dict | None:
        existing = await self.get(document_id)
        if existing is None:
            return None
        result = await asyncio.to_thread(
            lambda: self.db.table(_DOCUMENTS_TABLE)
            .update(patch)
            .eq("id", document_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )
        return result.data[0] if result.data else None

    async def update_totals(
        self,
        document_id: str,
        *,
        subtotal: Decimal,
        tax_total: Decimal,
        total: Decimal,
    ) -> None:
        await asyncio.to_thread(
            lambda: self.db.table(_DOCUMENTS_TABLE)
            .update(
                {
                    "subtotal": str(subtotal),
                    "tax_total": str(tax_total),
                    "total": str(total),
                }
            )
            .eq("id", document_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )

    async def sum_linked_bill_total(
        self,
        document_id: str,
        *,
        exclude_bill_id: str | None = None,
    ) -> Decimal:
        result = await asyncio.to_thread(
            lambda: self.db.table("bills")
            .select("id,total,status")
            .eq("tenant_id", self.tenant_id)
            .eq("purchase_order_id", document_id)
            .is_("deleted_at", "null")
            .execute()
        )
        total = Decimal("0")
        for row in result.data or []:
            if exclude_bill_id and str(row.get("id")) == exclude_bill_id:
                continue
            if row.get("status") in {"approved", "partially_paid", "paid"}:
                total += Decimal(str(row.get("total") or "0"))
        return total
