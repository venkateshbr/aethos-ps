"""Unit tests for accrual_agent WIP journal proposals."""

from __future__ import annotations

from typing import Any

import pytest

from app.agents.accrual_agent import (
    AccrualProposalError,
    build_employee_reimbursement_accrual_proposals,
    build_wip_accrual_proposals,
    write_employee_reimbursement_accrual_suggestions,
    write_wip_accrual_suggestions,
)
from app.agents.base import AgentDeps

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-accrual-001"


class _Result:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _Query:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self._filters: list[tuple[str, str, Any]] = []

    def select(self, _columns: str) -> _Query:
        return self

    def eq(self, field: str, value: Any) -> _Query:
        self._filters.append(("eq", field, value))
        return self

    def in_(self, field: str, values: list[Any]) -> _Query:
        self._filters.append(("in", field, values))
        return self

    def gte(self, field: str, value: Any) -> _Query:
        self._filters.append(("gte", field, value))
        return self

    def lte(self, field: str, value: Any) -> _Query:
        self._filters.append(("lte", field, value))
        return self

    def is_(self, field: str, value: str) -> _Query:
        self._filters.append(("is", field, value))
        return self

    def execute(self) -> _Result:
        return _Result([row for row in self._rows if self._matches(row)])

    def _matches(self, row: dict) -> bool:
        for op, field, value in self._filters:
            current = row.get(field)
            if op == "eq" and current != value:
                return False
            if op == "in" and current not in value and str(current) not in {str(v) for v in value}:
                return False
            if op == "gte" and str(current or "") < str(value):
                return False
            if op == "lte" and str(current or "") > str(value):
                return False
            if op == "is" and value == "null" and current is not None:
                return False
        return True


class _Db:
    def __init__(self, tables: dict[str, list[dict]]) -> None:
        self.tables = tables

    def table(self, name: str) -> _Query:
        return _Query(self.tables.get(name, []))


def _deps(tables: dict[str, list[dict]]) -> AgentDeps:
    return AgentDeps(tenant_id=TENANT_ID, user_id="user-001", db=_Db(tables))  # type: ignore[arg-type]


def _base_tables() -> dict[str, list[dict]]:
    return {
        "accounts": [
            {"tenant_id": TENANT_ID, "id": "ar-account", "code": "1200", "deleted_at": None},
            {"tenant_id": TENANT_ID, "id": "rev-account", "code": "4000", "deleted_at": None},
            {
                "tenant_id": TENANT_ID,
                "id": "employee-expense-account",
                "code": "5100",
                "deleted_at": None,
            },
            {
                "tenant_id": TENANT_ID,
                "id": "accrued-reimbursement-account",
                "code": "2100",
                "deleted_at": None,
            },
        ],
        "time_entries": [
            {
                "tenant_id": TENANT_ID,
                "id": "te-1",
                "project_id": "project-1",
                "employee_id": "employee-1",
                "hours": "10.00",
                "billing_status": "unbilled",
                "billable": True,
                "status": "approved",
                "date": "2026-06-10",
                "deleted_at": None,
            },
            {
                "tenant_id": TENANT_ID,
                "id": "te-2",
                "project_id": "project-2",
                "employee_id": "employee-2",
                "hours": "5.00",
                "billing_status": "unbilled",
                "billable": True,
                "status": "approved",
                "date": "2026-06-15",
                "deleted_at": None,
            },
            {
                "tenant_id": TENANT_ID,
                "id": "te-skipped",
                "project_id": "project-3",
                "employee_id": "employee-no-rate",
                "hours": "2.00",
                "billing_status": "unbilled",
                "billable": True,
                "status": "approved",
                "date": "2026-06-20",
                "deleted_at": None,
            },
        ],
        "employees": [
            {
                "tenant_id": TENANT_ID,
                "id": "employee-1",
                "default_bill_rate": "200.00",
                "default_bill_rate_currency": "USD",
                "deleted_at": None,
            },
            {
                "tenant_id": TENANT_ID,
                "id": "employee-2",
                "default_bill_rate": "100.00",
                "default_bill_rate_currency": "USD",
                "deleted_at": None,
            },
        ],
        "project_expenses": [
            {
                "tenant_id": TENANT_ID,
                "id": "expense-1",
                "project_id": "project-1",
                "amount": "185.50",
                "currency": "USD",
                "expense_date": "2026-06-12",
                "reimbursable": True,
                "reimbursed_at": None,
                "deleted_at": None,
            },
            {
                "tenant_id": TENANT_ID,
                "id": "expense-2",
                "project_id": "project-2",
                "amount": "64.50",
                "currency": "USD",
                "expense_date": "2026-06-18",
                "reimbursable": True,
                "reimbursed_at": None,
                "deleted_at": None,
            },
            {
                "tenant_id": TENANT_ID,
                "id": "expense-reimbursed",
                "project_id": "project-1",
                "amount": "100.00",
                "currency": "USD",
                "expense_date": "2026-06-20",
                "reimbursable": True,
                "reimbursed_at": "2026-06-21T00:00:00+00:00",
                "deleted_at": None,
            },
        ],
        "agent_suggestions": [],
    }


def test_build_wip_accrual_proposal_values_unbilled_time() -> None:
    proposals = build_wip_accrual_proposals(_deps(_base_tables()), "2026-06")

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.period == "2026-06"
    assert proposal.currency == "USD"
    assert proposal.unbilled_hours == "15.00"
    assert proposal.wip_value == "2500.00"
    assert proposal.project_count == 2
    assert proposal.time_entry_count == 2
    assert proposal.skipped_time_entry_count == 1
    assert proposal.confidence == 0.68
    assert proposal.journal_entry["entry_date"] == "2026-06-30"
    assert proposal.journal_entry["lines"][0]["direction"] == "DR"
    assert proposal.journal_entry["lines"][0]["account_id"] == "ar-account"
    assert proposal.journal_entry["lines"][1]["direction"] == "CR"
    assert proposal.journal_entry["lines"][1]["account_id"] == "rev-account"


def test_build_wip_accrual_proposal_raises_for_missing_account() -> None:
    tables = _base_tables()
    tables["accounts"] = [
        {"tenant_id": TENANT_ID, "id": "ar-account", "code": "1200", "deleted_at": None}
    ]

    with pytest.raises(AccrualProposalError) as exc_info:
        build_wip_accrual_proposals(_deps(tables), "2026-06")

    assert "4000" in str(exc_info.value)


def test_build_employee_reimbursement_accrual_values_unreimbursed_expenses() -> None:
    proposals = build_employee_reimbursement_accrual_proposals(
        _deps(_base_tables()),
        "2026-06",
    )

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.proposal_type == "employee_reimbursement_accrual"
    assert proposal.period == "2026-06"
    assert proposal.currency == "USD"
    assert proposal.expense_ids == ["expense-1", "expense-2"]
    assert proposal.expense_count == 2
    assert proposal.project_count == 2
    assert proposal.reimbursement_accrual_amount == "250.00"
    assert proposal.journal_entry["entry_date"] == "2026-06-30"
    assert proposal.journal_entry["lines"][0]["direction"] == "DR"
    assert proposal.journal_entry["lines"][0]["account_id"] == "employee-expense-account"
    assert proposal.journal_entry["lines"][1]["direction"] == "CR"
    assert proposal.journal_entry["lines"][1]["account_id"] == "accrued-reimbursement-account"


def test_build_employee_reimbursement_accrual_skips_already_accrued_expense() -> None:
    tables = _base_tables()
    tables["agent_suggestions"] = [
        {
            "tenant_id": TENANT_ID,
            "agent_name": "accrual_agent",
            "action_type": "draft_journal",
            "status": "approved",
            "output_snapshot": {
                "proposal_type": "employee_reimbursement_accrual",
                "period": "2026-06",
                "currency": "USD",
                "expense_ids": ["expense-1"],
                "reimbursement_accrual_amount": "185.50",
            },
        }
    ]

    proposals = build_employee_reimbursement_accrual_proposals(_deps(tables), "2026-06")

    assert len(proposals) == 1
    assert proposals[0].expense_ids == ["expense-2"]
    assert proposals[0].reimbursement_accrual_amount == "64.50"


@pytest.mark.asyncio
async def test_write_wip_accrual_suggestions_writes_l2_hitl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    async def _fake_write(*args: Any, **kwargs: Any) -> dict:
        calls.append(
            {
                "deps": args[0],
                **kwargs,
            }
        )
        return {"id": "suggestion-001"}

    monkeypatch.setattr("app.agents.accrual_agent.write_agent_suggestion", _fake_write)

    result = await write_wip_accrual_suggestions(_deps(_base_tables()), "2026-06")

    assert result["created_count"] == 1
    assert result["suggestion_ids"] == ["suggestion-001"]
    assert calls[0]["agent_name"] == "accrual_agent"
    assert calls[0]["action_type"] == "draft_journal"
    assert calls[0]["autonomy_level"] == 2
    assert calls[0]["output"]["journal_entry"]["lines"][0]["amount"] == "2500.00"


@pytest.mark.asyncio
async def test_write_wip_accrual_suggestions_skips_duplicate() -> None:
    tables = _base_tables()
    tables["agent_suggestions"] = [
        {
            "tenant_id": TENANT_ID,
            "agent_name": "accrual_agent",
            "action_type": "draft_journal",
            "status": "pending",
            "output_snapshot": {"period": "2026-06", "currency": "USD"},
        }
    ]

    result = await write_wip_accrual_suggestions(_deps(tables), "2026-06")

    assert result["created_count"] == 0
    assert result["skipped_duplicates"] == 1


@pytest.mark.asyncio
async def test_write_employee_reimbursement_accrual_suggestions_writes_l2_hitl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    async def _fake_write(*args: Any, **kwargs: Any) -> dict:
        calls.append({"deps": args[0], **kwargs})
        return {"id": "suggestion-expense-accrual-001"}

    monkeypatch.setattr("app.agents.accrual_agent.write_agent_suggestion", _fake_write)

    result = await write_employee_reimbursement_accrual_suggestions(
        _deps(_base_tables()),
        "2026-06",
    )

    assert result["created_count"] == 1
    assert result["suggestion_ids"] == ["suggestion-expense-accrual-001"]
    assert calls[0]["agent_name"] == "accrual_agent"
    assert calls[0]["action_type"] == "draft_journal"
    assert calls[0]["autonomy_level"] == 2
    assert calls[0]["output"]["reimbursement_accrual_amount"] == "250.00"
