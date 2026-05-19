"""Business logic for the Rate Cards resource."""

from __future__ import annotations

import logging

from app.models.rate_cards import (
    RateCardCreate,
    RateCardLineResponse,
    RateCardResponse,
)
from app.repositories.rate_cards_repo import RateCardRepository
from supabase import Client

logger = logging.getLogger(__name__)


def _to_response(card_row: dict, line_rows: list[dict]) -> RateCardResponse:
    return RateCardResponse(
        id=str(card_row["id"]),
        name=card_row["name"],
        currency=card_row["currency"],
        effective_date=str(card_row["effective_date"]),
        lines=[RateCardLineResponse.from_db(ln) for ln in line_rows],
    )


class RateCardService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self._repo = RateCardRepository(db, tenant_id)

    async def list_rate_cards(self) -> list[RateCardResponse]:
        cards = await self._repo.list()
        result: list[RateCardResponse] = []
        for card in cards:
            lines = await self._repo.get_lines(str(card["id"]))
            result.append(_to_response(card, lines))
        return result

    async def get_rate_card(self, id: str) -> RateCardResponse | None:
        card = await self._repo.get(id)
        if card is None:
            return None
        lines = await self._repo.get_lines(str(card["id"]))
        return _to_response(card, lines)

    async def create_rate_card(self, data: RateCardCreate) -> RateCardResponse:
        card_data = {
            "name": data.name,
            "currency": data.currency,
            "effective_date": data.effective_date.isoformat(),
        }
        line_data = [
            {"role": ln.role, "rate": str(ln.rate)}
            for ln in data.lines
        ]
        card = await self._repo.create(card_data, line_data)
        lines = await self._repo.get_lines(str(card["id"]))
        return _to_response(card, lines)
