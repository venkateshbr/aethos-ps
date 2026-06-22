"""Pydantic schemas for chart-of-accounts API responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

AccountType = Literal["asset", "liability", "equity", "revenue", "expense"]


class AccountResponse(BaseModel):
    """Chart-of-accounts row exposed to frontend account pickers."""

    id: str
    code: str
    name: str
    account_type: AccountType
    is_system: bool
    parent_id: str | None = None
