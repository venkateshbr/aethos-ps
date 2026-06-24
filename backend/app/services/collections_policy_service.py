"""Service layer for collections reminder policies."""

from __future__ import annotations

import asyncio
import logging

from app.models.collections_policy import (
    CollectionsPolicyConfig,
    CollectionsPolicyListResponse,
    CollectionsPolicyResponse,
    CollectionsPolicySource,
    CollectionsPolicyUpsert,
)
from supabase import Client

logger = logging.getLogger(__name__)

_TABLE = "collections_policies"


def default_collections_policy() -> CollectionsPolicyConfig:
    """Return the system default policy used when no DB row exists."""
    return CollectionsPolicyConfig()


def row_to_collections_policy(
    row: dict,
    *,
    source: CollectionsPolicySource,
) -> CollectionsPolicyResponse:
    """Map a DB row to an API/runtime policy model."""
    return CollectionsPolicyResponse(
        id=str(row["id"]) if row.get("id") else None,
        client_id=str(row["client_id"]) if row.get("client_id") else None,
        policy_source=source,
        is_enabled=bool(row.get("is_enabled", True)),
        gentle_after_days=int(row.get("gentle_after_days", 1)),
        firm_after_days=int(row.get("firm_after_days", 8)),
        final_after_days=int(row.get("final_after_days", 31)),
        cooldown_days=int(row.get("cooldown_days", 7)),
        max_reminders_per_invoice=int(row.get("max_reminders_per_invoice", 3)),
        max_auto_send_tone=row.get("max_auto_send_tone", "final"),
    )


class CollectionsPolicyService:
    """Tenant-scoped data access for collections policies."""

    def __init__(self, db: Client, tenant_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id

    async def list_policies(self) -> CollectionsPolicyListResponse:
        rows = await asyncio.to_thread(
            lambda: self._db.table(_TABLE)
            .select("*")
            .eq("tenant_id", self._tenant_id)
            .is_("deleted_at", "null")
            .order("client_id")
            .execute()
        )
        items = [
            row_to_collections_policy(
                row,
                source="client_override" if row.get("client_id") else "tenant_default",
            )
            for row in (rows.data or [])
        ]
        return CollectionsPolicyListResponse(items=items, total=len(items))

    async def get_effective_policy(
        self,
        client_id: str | None = None,
    ) -> CollectionsPolicyResponse:
        if client_id:
            client_policy = await self._find_policy(client_id=client_id)
            if client_policy is not None:
                return row_to_collections_policy(
                    client_policy,
                    source="client_override",
                )

        tenant_policy = await self._find_policy(client_id=None)
        if tenant_policy is not None:
            return row_to_collections_policy(
                tenant_policy,
                source="tenant_default",
            )

        return CollectionsPolicyResponse(**default_collections_policy().model_dump())

    async def upsert_default_policy(
        self,
        payload: CollectionsPolicyUpsert,
    ) -> CollectionsPolicyResponse:
        return await self._upsert_policy(client_id=None, payload=payload)

    async def upsert_client_policy(
        self,
        client_id: str,
        payload: CollectionsPolicyUpsert,
    ) -> CollectionsPolicyResponse:
        return await self._upsert_policy(client_id=client_id, payload=payload)

    async def _upsert_policy(
        self,
        *,
        client_id: str | None,
        payload: CollectionsPolicyUpsert,
    ) -> CollectionsPolicyResponse:
        existing = await self._find_policy(client_id=client_id)
        data = payload.model_dump()
        data["tenant_id"] = self._tenant_id
        data["client_id"] = client_id
        if existing:
            row_id = str(existing["id"])
            await asyncio.to_thread(
                lambda: self._db.table(_TABLE)
                .update(data)
                .eq("tenant_id", self._tenant_id)
                .eq("id", row_id)
                .execute()
            )
        else:
            created = await asyncio.to_thread(
                lambda: self._db.table(_TABLE).insert(data).execute()
            )
            row_id = str(created.data[0]["id"])

        refreshed = await self._get_policy_by_id(row_id)
        if refreshed is None:
            raise ValueError(f"Collections policy {row_id!r} not found after write")
        return row_to_collections_policy(
            refreshed,
            source="client_override" if client_id else "tenant_default",
        )

    async def _find_policy(self, *, client_id: str | None) -> dict | None:
        def _query() -> object:
            q = (
                self._db.table(_TABLE)
                .select("*")
                .eq("tenant_id", self._tenant_id)
                .is_("deleted_at", "null")
            )
            if client_id:
                q = q.eq("client_id", client_id)
            else:
                q = q.is_("client_id", "null")
            return q.limit(1).execute()

        result = await asyncio.to_thread(_query)
        rows = getattr(result, "data", None) or []
        return rows[0] if rows else None

    async def _get_policy_by_id(self, policy_id: str) -> dict | None:
        result = await asyncio.to_thread(
            lambda: self._db.table(_TABLE)
            .select("*")
            .eq("tenant_id", self._tenant_id)
            .eq("id", policy_id)
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None
