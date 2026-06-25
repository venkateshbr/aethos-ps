"""Manual journal service regression tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

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


class _RpcQuery:
    def execute(self) -> _Result:
        return _Result([{"id": "event-1"}])


class _FakeDb:
    def __init__(self) -> None:
        self.rpc_calls: list[tuple[str, dict]] = []

    def table(self, name: str) -> object:
        if name == "journal_lines":
            return _LinesQuery()
        if name == "journal_entries":
            return _ForbiddenJournalEntriesQuery()
        raise AssertionError(f"unexpected table: {name}")

    def rpc(self, name: str, params: dict) -> _RpcQuery:
        self.rpc_calls.append((name, params))
        return _RpcQuery()


@pytest.mark.asyncio
async def test_manual_journal_reference_does_not_update_posted_journal_entry() -> None:
    reason = "Accrue June payroll based on approved payroll register."
    payload = ManualJournalEntryIn.model_validate(
        {
            "description": "Month-end accrual",
            "reason": reason,
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
    db = _FakeDb()
    svc = ManualJournalService(
        db=db,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        user_id="user-1",
        actor_role="manager",
    )
    post_mock = MagicMock(
        return_value={
            "id": "journal-1",
            "entry_number": "JE-1",
            "description": "Month-end accrual",
            "reason": reason,
            "entry_date": "2026-06-22",
            "period": "2026-06",
            "reference_type": "manual",
            "reference_id": None,
            "created_by": "user-1",
            "posted_at": "2026-06-22T00:00:00Z",
        }
    )

    with (
        patch("app.services.manual_journal_service.assert_period_open", new=AsyncMock()),
        patch("app.services.manual_journal_service.post_journal", post_mock),
    ):
        response = await svc.post_manual_journal(payload)

    assert response.id == "journal-1"
    assert response.reference is None
    assert response.reason == reason
    assert post_mock.call_args.kwargs["extra_entry_fields"] == {"reason": reason}
    assert db.rpc_calls[0][0] == "append_financial_event"
    event = db.rpc_calls[0][1]
    assert event["p_event_type"] == "manual_journal.posted"
    assert event["p_actor_role"] == "manager"
    assert event["p_metadata"]["reason"] == reason
    assert event["p_metadata"]["total_debits"] == "100.00"


def test_manual_journal_requires_business_reason() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ManualJournalEntryIn.model_validate(
            {
                "description": "Month-end accrual",
                "entry_date": "2026-06-22",
                "lines": [
                    {
                        "direction": "DR",
                        "account_id": "11111111-1111-1111-1111-111111111111",
                        "amount": "100.00",
                        "currency": "USD",
                    },
                    {
                        "direction": "CR",
                        "account_id": "22222222-2222-2222-2222-222222222222",
                        "amount": "100.00",
                        "currency": "USD",
                    },
                ],
            }
        )

    assert "Reason is required" in str(exc_info.value)
