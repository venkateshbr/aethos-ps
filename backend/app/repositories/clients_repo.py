"""Repository: tenant-scoped CRUD for the clients table."""

from __future__ import annotations

import asyncio
import logging

from app.services.postgrest_errors import is_missing_column_error
from supabase import Client

logger = logging.getLogger(__name__)

_TABLE = "clients"

# Contacts with these kinds are valid in AR (invoice) contexts.
CUSTOMER_KINDS: tuple[str, ...] = ("customer", "both")
# Contacts with these kinds are valid in AP (bill) contexts.
VENDOR_KINDS: tuple[str, ...] = ("vendor", "both")

_OPTIONAL_VENDOR_CONTROL_FIELDS = frozenset(
    {
        "vendor_bank_account_status",
        "vendor_tax_validation_status",
        "vendor_sanctions_status",
        "vendor_remittance_status",
        "vendor_remittance_email",
        "vendor_payment_controls",
        "vendor_onboarding_approved_at",
        "vendor_onboarding_approved_by",
    }
)


class ClientRepository:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _base_query(self):  # type: ignore[no-untyped-def]
        return (
            self.db.table(_TABLE)
            .select("*")
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list(
        self,
        kind: str | None = None,
        q: str | None = None,
    ) -> list[dict]:
        query = self._base_query()
        if kind:
            # A contact with kind='both' appears in both customer and vendor
            # filtered views.  Use an IN filter so 'both' contacts are always
            # included when the caller asks for 'customer' or 'vendor'.
            if kind == "customer":
                query = query.in_("kind", list(CUSTOMER_KINDS))
            elif kind == "vendor":
                query = query.in_("kind", list(VENDOR_KINDS))
            else:
                # Exact match for 'both' or any future kind value
                query = query.eq("kind", kind)
        if q:
            query = query.ilike("name", f"%{q}%")
        result = await asyncio.to_thread(lambda: query.execute())
        return result.data or []

    async def get(self, id: str) -> dict | None:
        result = await asyncio.to_thread(
            lambda: self._base_query().eq("id", id).execute()
        )
        return result.data[0] if result.data else None

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create(self, data: dict) -> dict:
        payload = {**data, "tenant_id": self.tenant_id}
        try:
            result = await asyncio.to_thread(
                lambda: self.db.table(_TABLE).insert(payload).execute()
            )
        except Exception as exc:
            if not is_missing_column_error(exc, _OPTIONAL_VENDOR_CONTROL_FIELDS):
                raise
            fallback_payload = _without_optional_vendor_control_fields(payload)
            if fallback_payload == payload:
                raise
            logger.warning(
                "clients table is missing optional vendor-control columns; "
                "retrying insert without those fields"
            )
            result = await asyncio.to_thread(
                lambda: self.db.table(_TABLE).insert(fallback_payload).execute()
            )
        return result.data[0]

    async def update(self, id: str, data: dict) -> dict | None:
        # Only update if the row belongs to this tenant
        existing = await self.get(id)
        if existing is None:
            return None
        try:
            result = await asyncio.to_thread(
                lambda: self.db.table(_TABLE)
                .update(data)
                .eq("id", id)
                .eq("tenant_id", self.tenant_id)
                .execute()
            )
        except Exception as exc:
            if not is_missing_column_error(exc, _OPTIONAL_VENDOR_CONTROL_FIELDS):
                raise
            fallback_data = _without_optional_vendor_control_fields(data)
            if fallback_data == data:
                raise
            if not fallback_data:
                logger.warning(
                    "clients table is missing optional vendor-control columns; "
                    "skipping update because no supported fields remain"
                )
                return existing
            logger.warning(
                "clients table is missing optional vendor-control columns; "
                "retrying update without those fields"
            )
            result = await asyncio.to_thread(
                lambda: self.db.table(_TABLE)
                .update(fallback_data)
                .eq("id", id)
                .eq("tenant_id", self.tenant_id)
                .execute()
            )
        return result.data[0] if result.data else None


def _without_optional_vendor_control_fields(payload: dict) -> dict:
    return {
        key: value
        for key, value in payload.items()
        if key not in _OPTIONAL_VENDOR_CONTROL_FIELDS
    }
