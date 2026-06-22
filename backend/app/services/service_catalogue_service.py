"""Business logic for the Service Catalogue resource.

Pattern: Service layer sits between the router (thin) and the DB. All queries
are tenant-scoped — the service never touches rows from another tenant.

Money rule: default_rate is stored as NUMERIC(15,2) in the DB and serialised as
a string in the returned model (never float).

System services (is_system=True) are seeded by migration 0033. They can be
updated (name / rate overrides) but cannot be deactivated, to preserve
catalogue integrity.
"""

from __future__ import annotations

import asyncio
import logging

from app.models.service_catalogue import (
    ServiceCatalogueCreate,
    ServiceCatalogueItem,
    ServiceCatalogueListResponse,
    ServiceCatalogueUpdate,
)
from supabase import Client

logger = logging.getLogger(__name__)

_TABLE = "service_catalogue"


def _row_to_item(r: dict) -> ServiceCatalogueItem:
    """Map a raw DB row (with optional embedded revenue_account join) to the model."""
    acct = r.get("revenue_account") or {}
    # PostgREST returns embedded FK as a dict or None; guard both.
    if isinstance(acct, list):
        acct = acct[0] if acct else {}

    return ServiceCatalogueItem(
        id=str(r["id"]),
        code=r["code"],
        name=r["name"],
        description=r.get("description"),
        service_line=r["service_line"],
        billing_unit=r["billing_unit"],
        default_rate=str(r["default_rate"]) if r.get("default_rate") is not None else None,
        default_currency=r.get("default_currency", "GBP"),
        revenue_account_id=str(r["revenue_account_id"]) if r.get("revenue_account_id") else None,
        revenue_account_code=acct.get("code"),
        revenue_account_name=acct.get("name"),
        is_active=r["is_active"],
        is_system=r["is_system"],
    )


class ServiceCatalogueService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list_services(
        self,
        service_line: str | None = None,
        active_only: bool = True,
    ) -> ServiceCatalogueListResponse:
        q = (
            self._db.table(_TABLE)
            .select("*, revenue_account:accounts(code, name)")
            .eq("tenant_id", self._tenant_id)
        )
        if active_only:
            q = q.eq("is_active", True)
        if service_line:
            q = q.eq("service_line", service_line)
        q = q.order("service_line").order("code")

        rows = await asyncio.to_thread(lambda: q.execute())
        items = [_row_to_item(r) for r in (rows.data or [])]
        return ServiceCatalogueListResponse(items=items, total=len(items))

    async def get_service(self, id: str) -> ServiceCatalogueItem | None:
        result = await asyncio.to_thread(
            lambda: self._db.table(_TABLE)
            .select("*, revenue_account:accounts(code, name)")
            .eq("tenant_id", self._tenant_id)
            .eq("id", id)
            .execute()
        )
        if not result.data:
            return None
        return _row_to_item(result.data[0])

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create_service(
        self, payload: ServiceCatalogueCreate
    ) -> ServiceCatalogueItem:
        data: dict = {
            "tenant_id": self._tenant_id,
            "code": payload.code,
            "name": payload.name,
            "service_line": payload.service_line,
            "billing_unit": payload.billing_unit,
            "default_currency": payload.default_currency,
            "is_system": False,
        }
        if payload.description is not None:
            data["description"] = payload.description
        if payload.default_rate is not None:
            data["default_rate"] = payload.default_rate
        if payload.revenue_account_id is not None:
            data["revenue_account_id"] = payload.revenue_account_id

        result = await asyncio.to_thread(
            lambda: self._db.table(_TABLE).insert(data).execute()
        )
        row = result.data[0]
        # Re-fetch with the account join so the response is consistent with GET.
        return await self._get_or_raise(str(row["id"]))

    async def update_service(
        self, id: str, payload: ServiceCatalogueUpdate
    ) -> ServiceCatalogueItem | None:
        # Tenant guard — ensure the row belongs to us before touching it.
        existing = await self.get_service(id)
        if existing is None:
            return None

        patch = payload.model_dump(exclude_none=True)
        if patch:
            await asyncio.to_thread(
                lambda: self._db.table(_TABLE)
                .update(patch)
                .eq("tenant_id", self._tenant_id)
                .eq("id", id)
                .execute()
            )

        return await self._get_or_raise(id)

    async def deactivate_service(self, id: str) -> None:
        """Soft-delete a service by flipping is_active=False.

        Raises ValueError if not found.
        Raises PermissionError if is_system=True (system services are permanent).
        """
        existing = await self.get_service(id)
        if existing is None:
            raise ValueError(f"Service {id!r} not found")
        if existing.is_system:
            raise PermissionError(
                "System services cannot be deactivated. "
                "Use ServiceCatalogueUpdate to override name/rate instead."
            )
        await asyncio.to_thread(
            lambda: self._db.table(_TABLE)
            .update({"is_active": False})
            .eq("tenant_id", self._tenant_id)
            .eq("id", id)
            .execute()
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_or_raise(self, id: str) -> ServiceCatalogueItem:
        item = await self.get_service(id)
        if item is None:
            raise ValueError(f"Service {id!r} not found after write")
        return item
