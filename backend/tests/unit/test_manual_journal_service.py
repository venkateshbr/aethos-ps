"""Manual journal service regression tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.models.accounting import ManualJournalEntryIn
from app.services.manual_journal_service import ManualJournalService

pytestmark = pytest.mark.unit


class _Result:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _LinesQuery:
    def select(self, _columns: str) -> _LinesQuery:
        return self

    def eq(self, _key: str, _value: str) -> _LinesQuery:
        return self

    def execute(self) -> _Result:
        return _Result(
            [
                {
                    "id": "line-dr",
                    "direction": "DR",
                    "account_id": "11111111-1111-1111-1111-111111111111",
                    "amount": "100.00",
                    "currency": "USD",
                    "base_amount": "100.00",
                    "description": "Debit",
                },
                {
                    "id": "line-cr",
                    "direction": "CR",
                    "account_id": "22222222-2222-2222-2222-222222222222",
                    "amount": "100.00",
                    "currency": "USD",
                    "base_amount": "100.00",
                    "description": "Credit",
                },
            ]
        )


class _ForbiddenJournalEntriesQuery:
    def update(self, _payload: dict) -> _ForbiddenJournalEntriesQuery:
        raise AssertionError("posted manual journal must not update journal_entries.reference")


class _FakeDb:
    def table(self, name: str) -> object:
        if name == "journal_lines":
            return _LinesQuery()
        if name == "journal_entries":
            return _ForbiddenJournalEntriesQuery()
        raise AssertionError(f"unexpected table: {name}")


@pytest.mark.asyncio
async def test_manual_journal_reference_does_not_update_posted_journal_entry() -> None:
    payload = ManualJournalEntryIn.model_validate(
        {
            "description": "Month-end accrual",
            "entry_date": "2026-06-22",
            "reference": "ACCRUAL-001",
            "lines": [
                {
                    "direction": "DR",
                    "account_id": "11111111-1111-1111-1111-111111111111",
                    "amount": "100.00",
                    "currency": "USD",
                    "description": "Debit",
                },
                {
                    "direction": "CR",
                    "account_id": "22222222-2222-2222-2222-222222222222",
                    "amount": "100.00",
                    "currency": "USD",
                    "description": "Credit",
                },
            ],
        }
    )
    svc = ManualJournalService(db=_FakeDb(), tenant_id="tenant-1", user_id="user-1")  # type: ignore[arg-type]

    with (
        patch("app.services.manual_journal_service.assert_period_open", new=AsyncMock()),
        patch(
            "app.services.manual_journal_service.post_journal",
            return_value={
                "id": "journal-1",
                "entry_number": "JE-1",
                "description": "Month-end accrual",
                "entry_date": "2026-06-22",
                "period": "2026-06",
                "reference_type": "manual",
                "reference_id": None,
                "created_by": "user-1",
                "posted_at": "2026-06-22T00:00:00Z",
            },
        ),
    ):
        response = await svc.post_manual_journal(payload)

    assert response.id == "journal-1"
    assert response.reference is None
