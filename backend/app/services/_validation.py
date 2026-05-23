"""Shared validation helpers for the service layer.

These exist to keep the tenant-isolation rule visible and DRY across every
write path that references a tenant-scoped table by FK.

Why a helper and not RLS alone:
  RLS protects READ paths — tenant A can't SELECT tenant B's clients row.
  But a write path that INSERTs ``engagements(client_id = <tenant_b_id>)``
  using the service-role client bypasses RLS, so the row lands. The FK
  constraint still succeeds because the referenced ``clients.id`` exists.
  Result: tenant A's engagement now points at a foreign client_id (bug #92).
  Every service that takes a FK from a tenant-scoped table must call
  ``assert_belongs_to_tenant`` before insert.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import HTTPException, status
from supabase import Client

logger = logging.getLogger(__name__)


async def assert_belongs_to_tenant(
    db: Client,
    table: str,
    id_value: str,
    tenant_id: str,
    *,
    not_found_detail: str | None = None,
) -> None:
    """Raise 404 unless ``table`` contains a row with the given id and tenant_id.

    Uses 404 (not 403) deliberately: the requester does not get to learn
    whether the row exists in another tenant. From their perspective the row
    simply does not exist.

    Soft-deleted rows (``deleted_at IS NOT NULL``) are treated as not-found —
    matches the rest of the read path.

    Runs the Supabase query off the event loop via ``asyncio.to_thread`` so we
    don't block the FastAPI worker.
    """
    def _query() -> object:
        q = (
            db.table(table)
            .select("id")
            .eq("id", id_value)
            .eq("tenant_id", tenant_id)
            .limit(1)
        )
        # Several tenant-scoped tables in our schema use ``deleted_at`` for
        # soft delete. Apply the filter only if the column exists; we detect
        # that by simply attempting and falling back on error. The cheap path
        # is the success case — these tables all have the column.
        try:
            q = q.is_("deleted_at", "null")
        except Exception:  # pragma: no cover — defensive only
            pass
        return q.execute()

    try:
        result = await asyncio.to_thread(_query)
    except Exception as exc:
        # Some tables (rate_cards, employees) may not have deleted_at — retry
        # without the soft-delete filter so we don't false-404.
        logger.debug(
            "assert_belongs_to_tenant: retry without deleted_at filter for table=%s err=%s",
            table,
            exc,
        )

        def _fallback() -> object:
            return (
                db.table(table)
                .select("id")
                .eq("id", id_value)
                .eq("tenant_id", tenant_id)
                .limit(1)
                .execute()
            )

        result = await asyncio.to_thread(_fallback)

    rows = getattr(result, "data", None) or []
    if not rows:
        detail = not_found_detail or f"{table.rstrip('s').title()} not found"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


__all__ = ["assert_belongs_to_tenant"]
