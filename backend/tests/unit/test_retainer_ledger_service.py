"""Unit tests for retainer ledger helpers."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any

import pytest

from app.services.retainer_ledger_service import (
    record_retainer_draw,
    retainer_balance_for_engagement,
)

pytestmark = pytest.mark.unit


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _FakeDb, rows: list[dict[str, Any]]) -> None:
        self.db = db
        self.rows = list(rows)
        self.limit_count: int | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self.rows = [row for row in self.rows if row.get(key) == value]
        return self

    def is_(self, key: str, value: Any) -> _Query:
        if value == "null":
            self.rows = [row for row in self.rows if row.get(key) is None]
        return self

    def limit(self, count: int) -> _Query:
        self.limit_count = count
        return self

    def insert(self, payload: dict[str, Any]) -> _Query:
        row = {"id": f"ledger-{len(self.db.rows) + 1}", "deleted_at": None, **payload}
        self.db.rows.append(row)
        self.rows = [row]
        return self

    def execute(self) -> _Result:
        rows = self.rows[: self.limit_count] if self.limit_count is not None else self.rows
        return _Result(deepcopy(rows))


class _FakeDb:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def table(self, name: str) -> _Query:
        assert name == "retainer_ledger_entries"
        return _Query(self, self.rows)


def test_retainer_balance_applies_credits_and_debits() -> None:
    balance, has_entries = retainer_balance_for_engagement(
        _FakeDb(
            [
                {
                    "tenant_id": "tenant-1",
                    "engagement_id": "eng-1",
                    "entry_type": "deposit",
                    "amount": "2000.00",
                    "deleted_at": None,
                },
                {
                    "tenant_id": "tenant-1",
                    "engagement_id": "eng-1",
                    "entry_type": "draw",
                    "amount": "750.00",
                    "deleted_at": None,
                },
                {
                    "tenant_id": "tenant-1",
                    "engagement_id": "eng-1",
                    "entry_type": "debit_adjustment",
                    "amount": "50.00",
                    "deleted_at": None,
                },
            ]
        ),
        "tenant-1",
        "eng-1",
    )

    assert has_entries is True
    assert balance == Decimal("1200.00")


@pytest.mark.asyncio
async def test_record_retainer_draw_is_idempotent_by_invoice() -> None:
    db = _FakeDb(
        [
            {
                "id": "existing-draw",
                "tenant_id": "tenant-1",
                "engagement_id": "eng-1",
                "invoice_id": "invoice-1",
                "entry_type": "draw",
                "amount": "100.00",
                "deleted_at": None,
            }
        ]
    )

    row = await record_retainer_draw(
        db,
        tenant_id="tenant-1",
        engagement_id="eng-1",
        invoice_id="invoice-1",
        amount=Decimal("100.00"),
        currency="USD",
        description="Duplicate draw",
    )

    assert row is not None
    assert row["id"] == "existing-draw"
    assert len(db.rows) == 1
