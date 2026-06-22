"""Manual journal entry service.

Handles posting of manual GL adjustments (accruals, corrections, period-end
entries). Every manual entry is gated by:

  1. Period lock check (via period_lock_service.assert_period_open).
  2. accounting_guardian L3 validation (balance, period lock, account validity).
  3. post_journal() insertion (journal_entries + journal_lines rows).

The accounting_guardian always runs at L3 and cannot be bypassed.
"""

from __future__ import annotations

import asyncio
import logging

from app.domain.journal_helper import JournalLineSpec, post_journal
from app.models.accounting import (
    JournalEntryListItem,
    ManualJournalEntryIn,
    ManualJournalEntryResponse,
)
from app.services.period_lock_service import assert_period_open
from supabase import Client

logger = logging.getLogger(__name__)


class ManualJournalService:
    """Service for posting and listing manual GL journal entries."""

    def __init__(self, db: Client, tenant_id: str, user_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def post_manual_journal(
        self, payload: ManualJournalEntryIn
    ) -> ManualJournalEntryResponse:
        """Validate and post a manual journal entry.

        Steps:
          1. Assert the entry_date is in an open period.
          2. Build JournalLineSpec list from the request lines.
          3. Call post_journal() — which runs accounting_guardian internally.
          4. Fetch journal_lines and return response.

        Raises:
            HTTPException 422 if the period is locked.
            ValueError (re-raised as HTTPException 422) if the guardian rejects
            the journal (imbalanced, unknown accounts).
        """
        # 1. Period lock check — raises 422 with code=period_locked if locked
        await assert_period_open(self.db, self.tenant_id, payload.entry_date)

        # 2. Build JournalLineSpec list
        # account_id is a UUID from Pydantic; convert to str for the guardian
        lines = [
            JournalLineSpec(
                direction=line.direction,
                account_code="",  # not required for manual entries (guardian uses account_id)
                account_id=str(line.account_id),
                amount=line.amount,
                currency=line.currency,
                description=line.description or "",
                base_amount=line.amount,  # TODO: FX convert if currency != tenant base currency
            )
            for line in payload.lines
        ]

        # 3. Call post_journal (runs accounting_guardian → DB insert)
        # post_journal is synchronous (supabase-py is sync); run in thread
        def _post() -> dict:
            return post_journal(
                db=self.db,
                tenant_id=self.tenant_id,
                created_by=self.user_id,
                description=payload.description,
                entry_date=payload.entry_date.isoformat(),
                reference_type="manual",
                reference_id=None,  # no sub-ledger reference for manual entries
                lines=lines,
            )

        try:
            je = await asyncio.to_thread(_post)
        except ValueError as exc:
            # accounting_guardian rejected — bubble up as 422
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        # Store reference on the journal_entries row if supplied
        if payload.reference:
            await asyncio.to_thread(
                lambda: self.db.table("journal_entries")
                .update({"reference": payload.reference})
                .eq("id", je["id"])
                .execute()
            )
            je["reference"] = payload.reference

        # 4. Fetch journal_lines for the response
        def _fetch_lines() -> list[dict]:
            result = (
                self.db.table("journal_lines")
                .select("*")
                .eq("journal_entry_id", je["id"])
                .execute()
            )
            return result.data or []

        je_lines = await asyncio.to_thread(_fetch_lines)

        logger.info(
            "Manual journal posted",
            extra={
                "journal_entry_id": je["id"],
                "tenant_id": self.tenant_id,
                "user_id": self.user_id,
                "lines": len(je_lines),
            },
        )

        return ManualJournalEntryResponse.from_db(je, je_lines)

    async def list_journal_entries(
        self,
        *,
        reference_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[JournalEntryListItem]:
        """List journal entries for this tenant, optionally filtered by reference_type.

        Args:
            reference_type: Filter to a specific type (e.g. "manual", "invoice", "bill").
            limit: Maximum rows to return (capped at 100).
            offset: Pagination offset.

        Returns:
            List of JournalEntryListItem in descending posted_at order.
        """

        def _fetch() -> list[dict]:
            query = (
                self.db.table("journal_entries")
                .select(
                    "id, entry_number, description, entry_date, period, "
                    "reference_type, reference_id, created_by, posted_at"
                )
                .eq("tenant_id", self.tenant_id)
                .order("posted_at", desc=True)
                .limit(min(limit, 100))
                .offset(offset)
            )
            if reference_type is not None:
                query = query.eq("reference_type", reference_type)
            return query.execute().data or []

        rows = await asyncio.to_thread(_fetch)

        return [
            JournalEntryListItem(
                id=str(r["id"]),
                entry_number=str(r["entry_number"]),
                description=str(r["description"]),
                entry_date=str(r["entry_date"]),
                period=str(r["period"]),
                reference_type=str(r["reference_type"]),
                reference=r.get("reference_id"),
                created_by=str(r["created_by"]),
                posted_at=str(r["posted_at"]),
            )
            for r in rows
        ]
