"""Pydantic request/response schemas for the Rate Cards API.

Money fields (rate) are Decimal in Python and serialised as 2dp str in JSON
via ``app.domain.money.serialise_money`` (bug #93).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.domain.money import serialise_money


class RateCardLineCreate(BaseModel):
    role: str = Field(..., min_length=1, max_length=100)
    rate: Decimal = Field(..., ge=Decimal("0"), decimal_places=2)

    @field_validator("rate", mode="before")
    @classmethod
    def coerce_rate(cls, v: object) -> Decimal:
        return Decimal(str(v))


class RateCardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    effective_date: date
    lines: list[RateCardLineCreate] = Field(..., min_length=1)


class RateCardLineResponse(BaseModel):
    role: str
    rate: str  # serialised as string

    @classmethod
    def from_db(cls, row: dict) -> RateCardLineResponse:
        return cls(role=row["role"], rate=serialise_money(row["rate"]) or "0.00")


class RateCardResponse(BaseModel):
    id: str
    name: str
    currency: str
    effective_date: str
    lines: list[RateCardLineResponse]
