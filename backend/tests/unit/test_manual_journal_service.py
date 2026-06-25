"""Manual journal service regression tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.accounting import (
    ManualJournalApprovalTaskResponse,
    ManualJournalEntryIn,
    ManualJournalEntryResponse,
    ManualJournalReversalIn,
)
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


class _ThresholdQuery:
    def __init__(self, db: _ThresholdDb, table: str) -> None:
        self.db = db
        self.table = table
        self._insert_payload: dict | None = None

    def select(self, _columns: str = "*") -> _ThresholdQuery:
        return self

    def eq(self, _key: str, _value: str) -> _ThresholdQuery:
        return self

    def limit(self, _count: int) -> _ThresholdQuery:
        return self

    def insert(self, payload: dict) -> _ThresholdQuery:
        self._insert_payload = dict(payload)
        return self

    def execute(self) -> _Result:
        if self._insert_payload is not None:
            row = {
                "id": f"{self.table}-1",
                **self._insert_payload,
            }
            self.db.tables[self.table].append(row)
            return _Result([row])
        return _Result(self.db.tables[self.table])


class _ThresholdDb:
    def __init__(self, *, threshold: str) -> None:
        self.tables: dict[str, list[dict]] = {
            "tenant_approval_policies": [
                {
                    "tenant_id": "tenant-1",
                    "manual_journal_approval_threshold": threshold,
                    "accounting_role": "admin",
                }
            ],
            "agent_suggestions": [],
            "hitl_tasks": [],
        }

    def table(self, name: str) -> _ThresholdQuery:
        if name not in self.tables:
            raise AssertionError(f"unexpected table: {name}")
        return _ThresholdQuery(self, name)


class _ReversalQuery:
    def __init__(self, db: _ReversalDb, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, object]] = []
        self._limit: int | None = None

    def select(self, _columns: str = "*") -> _ReversalQuery:
        return self

    def eq(self, key: str, value: object) -> _ReversalQuery:
        self._eq_filters.append((key, value))
        return self

    def limit(self, count: int) -> _ReversalQuery:
        self._limit = count
        return self

    def execute(self) -> _Result:
        rows = list(self.db.tables[self.table])
        for key, value in self._eq_filters:
            rows = [row for row in rows if str(row.get(key)) == str(value)]
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Result(rows)


class _ReversalDb:
    def __init__(
        self,
        *,
        original_reference_type: str = "manual",
        existing_reversal: bool = False,
    ) -> None:
        self.rpc_calls: list[tuple[str, dict]] = []
        self.tables: dict[str, list[dict]] = {
            "journal_entries": [
                {
                    "id": "journal-1",
                    "tenant_id": "tenant-1",
                    "entry_number": "JE-1",
                    "description": "Month-end accrual",
                    "reason": "Original accrual reason",
                    "entry_date": "2026-06-22",
                    "period": "2026-06",
                    "reference_type": original_reference_type,
                    "reference_id": None,
                    "created_by": "user-1",
                    "posted_at": "2026-06-22T00:00:00Z",
                },
                {
                    "id": "journal-reversal",
                    "tenant_id": "tenant-1",
                    "entry_number": "JE-R1",
                    "description": "Reversal of JE-1",
                    "reason": "Reverse duplicate accrual after review.",
                    "entry_date": "2026-06-23",
                    "period": "2026-06",
                    "reference_type": "manual_reversal",
                    "reference_id": "journal-1",
                    "created_by": "user-1",
                    "posted_at": "2026-06-23T00:00:00Z",
                },
            ],
            "journal_lines": [
                {
                    "id": "line-dr",
                    "journal_entry_id": "journal-1",
                    "direction": "DR",
                    "account_id": "11111111-1111-1111-1111-111111111111",
                    "amount": "100.00",
                    "currency": "USD",
                    "base_amount": "100.00",
                    "description": "Debit",
                },
                {
                    "id": "line-cr",
                    "journal_entry_id": "journal-1",
                    "direction": "CR",
                    "account_id": "22222222-2222-2222-2222-222222222222",
                    "amount": "100.00",
                    "currency": "USD",
                    "base_amount": "100.00",
                    "description": "Credit",
                },
                {
                    "id": "line-rev-cr",
                    "journal_entry_id": "journal-reversal",
                    "direction": "CR",
                    "account_id": "11111111-1111-1111-1111-111111111111",
                    "amount": "100.00",
                    "currency": "USD",
                    "base_amount": "100.00",
                    "description": "Reversal credit",
                },
                {
                    "id": "line-rev-dr",
                    "journal_entry_id": "journal-reversal",
                    "direction": "DR",
                    "account_id": "22222222-2222-2222-2222-222222222222",
                    "amount": "100.00",
                    "currency": "USD",
                    "base_amount": "100.00",
                    "description": "Reversal debit",
                },
            ],
        }
        if not existing_reversal:
            self.tables["journal_entries"] = [
                row
                for row in self.tables["journal_entries"]
                if row["id"] != "journal-reversal"
            ]

    def table(self, name: str) -> _ReversalQuery:
        if name not in self.tables:
            raise AssertionError(f"unexpected table: {name}")
        return _ReversalQuery(self, name)

    def rpc(self, name: str, params: dict) -> _RpcQuery:
        self.rpc_calls.append((name, params))
        return _RpcQuery()


def _payload(*, amount: str = "100.00") -> ManualJournalEntryIn:
    return ManualJournalEntryIn.model_validate(
        {
            "description": "Month-end accrual",
            "reason": "Accrue June payroll based on approved payroll register.",
            "entry_date": "2026-06-22",
            "reference": "ACCRUAL-001",
            "lines": [
                {
                    "direction": "DR",
                    "account_id": "11111111-1111-1111-1111-111111111111",
                    "amount": amount,
                    "currency": "USD",
                    "description": "Debit",
                },
                {
                    "direction": "CR",
                    "account_id": "22222222-2222-2222-2222-222222222222",
                    "amount": amount,
                    "currency": "USD",
                    "description": "Credit",
                },
            ],
        }
    )


def _reversal_payload() -> ManualJournalReversalIn:
    return ManualJournalReversalIn.model_validate(
        {
            "entry_date": "2026-06-23",
            "reason": "Reverse duplicate accrual after controller review.",
        }
    )


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


@pytest.mark.asyncio
async def test_submit_manual_journal_below_threshold_posts_directly() -> None:
    db = _ThresholdDb(threshold="10000.00")
    svc = ManualJournalService(
        db=db,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        user_id="user-1",
        actor_role="manager",
    )
    direct_response = ManualJournalEntryResponse(
        id="journal-1",
        entry_number="JE-1",
        description="Month-end accrual",
        reason="Accrue June payroll based on approved payroll register.",
        entry_date="2026-06-22",
        period="2026-06",
        reference_type="manual",
        reference=None,
        created_by="user-1",
        posted_at="2026-06-22T00:00:00Z",
        lines=[],
    )

    with patch.object(
        svc,
        "post_manual_journal",
        new=AsyncMock(return_value=direct_response),
    ) as post_mock:
        result = await svc.submit_manual_journal(_payload(amount="9999.99"))

    assert result is direct_response
    post_mock.assert_awaited_once()
    assert db.tables["agent_suggestions"] == []
    assert db.tables["hitl_tasks"] == []


@pytest.mark.asyncio
async def test_submit_manual_journal_above_threshold_creates_inbox_task() -> None:
    db = _ThresholdDb(threshold="10000.00")
    svc = ManualJournalService(
        db=db,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        user_id="user-1",
        actor_role="manager",
    )

    with patch.object(
        svc,
        "post_manual_journal",
        new=AsyncMock(),
    ) as post_mock:
        result = await svc.submit_manual_journal(_payload(amount="15000.00"))

    assert isinstance(result, ManualJournalApprovalTaskResponse)
    assert result.status == "pending_approval"
    assert result.required_approval_role == "admin"
    assert result.approval_policy_reason == "manual_journal_above_approval_threshold"
    assert result.total_debits == "15000.00"
    assert result.threshold == "10000.00"
    post_mock.assert_not_awaited()
    suggestion = db.tables["agent_suggestions"][0]
    task = db.tables["hitl_tasks"][0]
    assert suggestion["action_type"] == "draft_journal"
    assert suggestion["output_snapshot"]["reason"].startswith("Accrue June payroll")
    assert suggestion["output_snapshot"]["total_debits"] == "15000.00"
    assert task["kind"] == "draft_journal"
    assert task["payload"]["manual_journal_approval"]["source"] == (
        "manual_journal_threshold"
    )


@pytest.mark.asyncio
async def test_reverse_manual_journal_posts_flipped_lines_and_audit_event() -> None:
    db = _ReversalDb()
    svc = ManualJournalService(
        db=db,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        user_id="user-1",
        actor_role="manager",
    )
    post_mock = MagicMock(
        return_value={
            "id": "journal-reversal",
            "entry_number": "JE-R1",
            "description": "Reversal of JE-1",
            "reason": "Reverse duplicate accrual after controller review.",
            "entry_date": "2026-06-23",
            "period": "2026-06",
            "reference_type": "manual_reversal",
            "reference_id": "journal-1",
            "created_by": "user-1",
            "posted_at": "2026-06-23T00:00:00Z",
        }
    )

    with (
        patch("app.services.manual_journal_service.assert_period_open", new=AsyncMock()),
        patch("app.services.manual_journal_service.post_journal", post_mock),
    ):
        response = await svc.reverse_manual_journal("journal-1", _reversal_payload())

    assert response.id == "journal-reversal"
    assert response.reference == "journal-1"
    call = post_mock.call_args.kwargs
    assert call["reference_type"] == "manual_reversal"
    assert call["reference_id"] == "journal-1"
    assert call["extra_entry_fields"]["reason"].startswith("Reverse duplicate")
    assert [line.direction for line in call["lines"]] == ["CR", "DR"]
    assert db.rpc_calls[0][0] == "append_financial_event"
    event = db.rpc_calls[0][1]
    assert event["p_event_type"] == "manual_journal.reversed"
    assert event["p_entity_id"] == "journal-1"
    assert event["p_source_id"] == "journal-reversal"
    assert event["p_metadata"]["total_debits"] == "100.00"
    assert event["p_metadata"]["reason"].startswith("Reverse duplicate")


@pytest.mark.asyncio
async def test_reverse_manual_journal_rejects_duplicate_reversal() -> None:
    svc = ManualJournalService(
        db=_ReversalDb(existing_reversal=True),  # type: ignore[arg-type]
        tenant_id="tenant-1",
        user_id="user-1",
        actor_role="manager",
    )

    with (
        patch("app.services.manual_journal_service.assert_period_open", new=AsyncMock()),
        pytest.raises(HTTPException) as exc_info,
    ):
        await svc.reverse_manual_journal("journal-1", _reversal_payload())

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_reverse_manual_journal_rejects_non_manual_entry() -> None:
    svc = ManualJournalService(
        db=_ReversalDb(original_reference_type="invoice"),  # type: ignore[arg-type]
        tenant_id="tenant-1",
        user_id="user-1",
        actor_role="manager",
    )

    with (
        patch("app.services.manual_journal_service.assert_period_open", new=AsyncMock()),
        pytest.raises(HTTPException) as exc_info,
    ):
        await svc.reverse_manual_journal("journal-1", _reversal_payload())

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_reverse_manual_journal_rejects_locked_period() -> None:
    svc = ManualJournalService(
        db=_ReversalDb(),  # type: ignore[arg-type]
        tenant_id="tenant-1",
        user_id="user-1",
        actor_role="manager",
    )

    with (
        patch(
            "app.services.manual_journal_service.assert_period_open",
            new=AsyncMock(side_effect=HTTPException(status_code=422, detail="locked")),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await svc.reverse_manual_journal("journal-1", _reversal_payload())

    assert exc_info.value.status_code == 422


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
