"""Unit tests for recurring journal proposal generation."""

from __future__ import annotations

from typing import Any

import pytest

from app.agents.base import AgentDeps
from app.agents.recurring_journal_agent import (
    RecurringJournalProposalError,
    build_recurring_journal_proposals,
    write_recurring_journal_suggestions,
)

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-recurring-001"


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
        "recurring_journal_templates": [
            {
                "id": "template-rent",
                "tenant_id": TENANT_ID,
                "name": "Monthly rent accrual",
                "description": "Office rent",
                "schedule_day": 31,
                "start_period": "2026-01",
                "end_period": None,
                "currency": "USD",
                "is_active": True,
                "deleted_at": None,
            },
            {
                "id": "template-future",
                "tenant_id": TENANT_ID,
                "name": "Future template",
                "schedule_day": 15,
                "start_period": "2026-08",
                "end_period": None,
                "currency": "USD",
                "is_active": True,
                "deleted_at": None,
            },
        ],
        "recurring_journal_template_lines": [
            {
                "id": "line-rent-dr",
                "tenant_id": TENANT_ID,
                "template_id": "template-rent",
                "account_id": "rent-expense-account",
                "direction": "DR",
                "amount": "2500.00",
                "description": "Rent expense",
                "order_index": 0,
            },
            {
                "id": "line-rent-cr",
                "tenant_id": TENANT_ID,
                "template_id": "template-rent",
                "account_id": "accrued-expense-account",
                "direction": "CR",
                "amount": "2500.00",
                "description": "Accrued rent",
                "order_index": 1,
            },
        ],
        "agent_suggestions": [],
    }


def test_build_recurring_journal_proposal_caps_schedule_day_to_month_end() -> None:
    proposals = build_recurring_journal_proposals(_deps(_base_tables()), "2026-02")

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.proposal_type == "recurring_journal"
    assert proposal.period == "2026-02"
    assert proposal.template_id == "template-rent"
    assert proposal.template_name == "Monthly rent accrual"
    assert proposal.entry_date == "2026-02-28"
    assert proposal.total_amount == "2500.00"
    assert proposal.journal_entry["reference"] == "recurring-journal:2026-02:template-rent"
    assert proposal.journal_entry["lines"][0]["direction"] == "DR"
    assert proposal.journal_entry["lines"][0]["currency"] == "USD"


def test_build_recurring_journal_respects_template_end_period() -> None:
    tables = _base_tables()
    tables["recurring_journal_templates"][0]["end_period"] = "2026-03"

    assert build_recurring_journal_proposals(_deps(tables), "2026-04") == []


def test_build_recurring_journal_skips_unbalanced_template() -> None:
    tables = _base_tables()
    tables["recurring_journal_template_lines"][1]["amount"] = "2400.00"

    assert build_recurring_journal_proposals(_deps(tables), "2026-02") == []


def test_build_recurring_journal_raises_for_invalid_period() -> None:
    with pytest.raises(RecurringJournalProposalError):
        build_recurring_journal_proposals(_deps(_base_tables()), "2026-13")


@pytest.mark.asyncio
async def test_write_recurring_journal_suggestions_writes_l2_hitl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    async def _fake_write(*args: Any, **kwargs: Any) -> dict:
        calls.append({"deps": args[0], **kwargs})
        return {"id": "suggestion-recurring-001"}

    monkeypatch.setattr(
        "app.agents.recurring_journal_agent.write_agent_suggestion",
        _fake_write,
    )

    result = await write_recurring_journal_suggestions(_deps(_base_tables()), "2026-02")

    assert result["created_count"] == 1
    assert result["suggestion_ids"] == ["suggestion-recurring-001"]
    assert calls[0]["agent_name"] == "recurring_journal_agent"
    assert calls[0]["action_type"] == "draft_journal"
    assert calls[0]["autonomy_level"] == 2
    assert calls[0]["related_entity_type"] == "recurring_journal_template"
    assert calls[0]["related_entity_id"] == "template-rent"
    assert calls[0]["output"]["total_amount"] == "2500.00"


@pytest.mark.asyncio
async def test_write_recurring_journal_suggestions_skips_duplicate() -> None:
    tables = _base_tables()
    tables["agent_suggestions"] = [
        {
            "tenant_id": TENANT_ID,
            "agent_name": "recurring_journal_agent",
            "action_type": "draft_journal",
            "status": "pending",
            "output_snapshot": {
                "proposal_type": "recurring_journal",
                "period": "2026-02",
                "template_id": "template-rent",
            },
        }
    ]

    result = await write_recurring_journal_suggestions(_deps(tables), "2026-02")

    assert result["created_count"] == 0
    assert result["skipped_duplicates"] == 1
