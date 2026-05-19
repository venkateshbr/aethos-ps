"""Repository: tenant-scoped CRUD for rate_cards and rate_card_lines."""

from __future__ import annotations

import asyncio
import logging

from supabase import Client

logger = logging.getLogger(__name__)

_TABLE = "rate_cards"
_LINES_TABLE = "rate_card_lines"


class RateCardRepository:
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

    async def list(self) -> list[dict]:
        result = await asyncio.to_thread(lambda: self._base_query().execute())
        return result.data or []

    async def get(self, id: str) -> dict | None:
        result = await asyncio.to_thread(
            lambda: self._base_query().eq("id", id).execute()
        )
        return result.data[0] if result.data else None

    async def get_lines(self, rate_card_id: str) -> list[dict]:
        result = await asyncio.to_thread(
            lambda: self.db.table(_LINES_TABLE)
            .select("*")
            .eq("rate_card_id", rate_card_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )
        return result.data or []

    # ------------------------------------------------------------------
    # Write — transactional insert of card + lines
    # Supabase-py does not expose DB transactions, so we insert lines
    # after the card. On error the card is orphaned but that is
    # acceptable for v1; a cleanup job can handle it.
    # ------------------------------------------------------------------

    async def create(self, card_data: dict, lines: list[dict]) -> dict:
        card_payload = {**card_data, "tenant_id": self.tenant_id}
        card_result = await asyncio.to_thread(
            lambda: self.db.table(_TABLE).insert(card_payload).execute()
        )
        card = card_result.data[0]
        card_id = card["id"]

        if lines:
            line_payloads = [
                {**line, "rate_card_id": card_id, "tenant_id": self.tenant_id}
                for line in lines
            ]
            await asyncio.to_thread(
                lambda: self.db.table(_LINES_TABLE).insert(line_payloads).execute()
            )

        return card
