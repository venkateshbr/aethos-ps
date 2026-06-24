"""Unit tests for prepaid expense amortization proposal generation."""

from __future__ import annotations

from typing import Any

import pytest

from app.agents.base import AgentDeps
from app.agents.prepaid_amortization_agent import (
    PrepaidAmortizationProposalError,
    build_prepaid_amortization_proposals,
    write_prepaid_amortization_suggestions,
)

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-prepaid-001"


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
            {
                "tenant_id": TENANT_ID,
                "id": "prepaid-account",
                "code": "1500",
                "deleted_at": None,
            },
            {
                "tenant_id": TENANT_ID,
                "id": "expense-account",
                "code": "5000",
                "deleted_at": None,
            },
        ],
        "bill_lines": [
            {
                "id": "bill-line-prepaid",
                "tenant_id": TENANT_ID,
                "bill_id": "bill-001",
                "description": "Annual software subscription",
                "amount": "900.00",
                "account_id": "software-expense-account",
                "is_prepaid": True,
                "service_start_date": "2026-06-01",
                "service_end_date": "2026-08-29",
            },
            {
                "id": "bill-line-expense",
                "tenant_id": TENANT_ID,
                "bill_id": "bill-001",
                "description": "One-time setup",
                "amount": "100.00",
                "account_id": None,
                "is_prepaid": False,
                "service_start_date": None,
                "service_end_date": None,
            },
        ],
        "bills": [
            {
                "id": "bill-001",
                "tenant_id": TENANT_ID,
                "bill_number": "BILL-0001",
                "status": "approved",
                "currency": "USD",
                "deleted_at": None,
            }
        ],
        "agent_suggestions": [],
    }


def test_build_prepaid_amortization_proposal_values_current_period() -> None:
    proposals = build_prepaid_amortization_proposals(_deps(_base_tables()), "2026-06")

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.proposal_type == "prepaid_expense_amortization"
    assert proposal.period == "2026-06"
    assert proposal.currency == "USD"
    assert proposal.bill_id == "bill-001"
    assert proposal.bill_line_id == "bill-line-prepaid"
    assert proposal.prepaid_amount == "900.00"
    assert proposal.prior_amortized_amount == "0.00"
    assert proposal.amortization_amount == "300.00"
    assert proposal.confidence == 0.82
    assert proposal.journal_entry["entry_date"] == "2026-06-30"
    assert proposal.journal_entry["reference"] == ("prepaid-amortization:2026-06:bill-line-prepaid")
    assert proposal.journal_entry["lines"][0]["direction"] == "DR"
    assert proposal.journal_entry["lines"][0]["account_id"] == "software-expense-account"
    assert proposal.journal_entry["lines"][1]["direction"] == "CR"
    assert proposal.journal_entry["lines"][1]["account_id"] == "prepaid-account"


def test_build_prepaid_amortization_final_period_uses_remaining_residual() -> None:
    tables = _base_tables()
    tables["agent_suggestions"] = [
        {
            "tenant_id": TENANT_ID,
            "agent_name": "prepaid_amortization_agent",
            "action_type": "draft_journal",
            "status": "approved",
            "output_snapshot": {
                "proposal_type": "prepaid_expense_amortization",
                "period": "2026-06",
                "bill_line_id": "bill-line-prepaid",
                "amortization_amount": "300.00",
            },
        },
        {
            "tenant_id": TENANT_ID,
            "agent_name": "prepaid_amortization_agent",
            "action_type": "draft_journal",
            "status": "approved",
            "output_snapshot": {
                "proposal_type": "prepaid_expense_amortization",
                "period": "2026-07",
                "bill_line_id": "bill-line-prepaid",
                "amortization_amount": "300.00",
            },
        },
    ]

    proposals = build_prepaid_amortization_proposals(_deps(tables), "2026-08")

    assert len(proposals) == 1
    assert proposals[0].prior_amortized_amount == "600.00"
    assert proposals[0].amortization_amount == "300.00"


def test_build_prepaid_amortization_returns_empty_without_overlap() -> None:
    proposals = build_prepaid_amortization_proposals(_deps(_base_tables()), "2026-09")

    assert proposals == []


def test_build_prepaid_amortization_raises_for_missing_accounts() -> None:
    tables = _base_tables()
    tables["accounts"] = []

    with pytest.raises(PrepaidAmortizationProposalError) as exc_info:
        build_prepaid_amortization_proposals(_deps(tables), "2026-06")

    assert "1500" in str(exc_info.value)
    assert "5000" in str(exc_info.value)


@pytest.mark.asyncio
async def test_write_prepaid_amortization_suggestions_writes_l2_hitl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    async def _fake_write(*args: Any, **kwargs: Any) -> dict:
        calls.append({"deps": args[0], **kwargs})
        return {"id": "suggestion-prepaid-001"}

    monkeypatch.setattr(
        "app.agents.prepaid_amortization_agent.write_agent_suggestion",
        _fake_write,
    )

    result = await write_prepaid_amortization_suggestions(
        _deps(_base_tables()),
        "2026-06",
    )

    assert result["created_count"] == 1
    assert result["suggestion_ids"] == ["suggestion-prepaid-001"]
    assert calls[0]["agent_name"] == "prepaid_amortization_agent"
    assert calls[0]["action_type"] == "draft_journal"
    assert calls[0]["autonomy_level"] == 2
    assert calls[0]["related_entity_type"] == "bill_line"
    assert calls[0]["related_entity_id"] == "bill-line-prepaid"
    assert calls[0]["output"]["amortization_amount"] == "300.00"


@pytest.mark.asyncio
async def test_write_prepaid_amortization_suggestions_skips_duplicate() -> None:
    tables = _base_tables()
    tables["agent_suggestions"] = [
        {
            "tenant_id": TENANT_ID,
            "agent_name": "prepaid_amortization_agent",
            "action_type": "draft_journal",
            "status": "approved_with_edits",
            "output_snapshot": {
                "proposal_type": "prepaid_expense_amortization",
                "period": "2026-06",
                "bill_line_id": "bill-line-prepaid",
            },
        }
    ]

    result = await write_prepaid_amortization_suggestions(_deps(tables), "2026-06")

    assert result["created_count"] == 0
    assert result["skipped_duplicates"] == 1
