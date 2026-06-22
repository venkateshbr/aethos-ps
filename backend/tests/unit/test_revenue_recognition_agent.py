"""Unit tests for deferred revenue release proposal generation."""

from __future__ import annotations

from typing import Any

import pytest

from app.agents.base import AgentDeps
from app.agents.revenue_recognition_agent import (
    RevenueRecognitionProposalError,
    build_deferred_revenue_release_proposals,
    write_deferred_revenue_release_suggestions,
)

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-revrec-001"


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
                "id": "deferred-account",
                "code": "2200",
                "deleted_at": None,
            },
            {
                "tenant_id": TENANT_ID,
                "id": "revenue-account",
                "code": "4000",
                "deleted_at": None,
            },
        ],
        "journal_lines": [
            {
                "tenant_id": TENANT_ID,
                "account_id": "deferred-account",
                "direction": "CR",
                "amount": "1200.00",
                "currency": "USD",
                "journal_entries": {
                    "period": "2026-06",
                    "posted_at": "2026-06-10T00:00:00+00:00",
                },
            },
            {
                "tenant_id": TENANT_ID,
                "account_id": "deferred-account",
                "direction": "DR",
                "amount": "200.00",
                "currency": "USD",
                "journal_entries": {
                    "period": "2026-06",
                    "posted_at": "2026-06-20T00:00:00+00:00",
                },
            },
            {
                "tenant_id": TENANT_ID,
                "account_id": "deferred-account",
                "direction": "CR",
                "amount": "999.00",
                "currency": "USD",
                "journal_entries": {
                    "period": "2026-05",
                    "posted_at": "2026-05-20T00:00:00+00:00",
                },
            },
            {
                "tenant_id": TENANT_ID,
                "account_id": "deferred-account",
                "direction": "CR",
                "amount": "300.00",
                "currency": "USD",
                "journal_entries": {
                    "period": "2026-06",
                    "posted_at": None,
                },
            },
        ],
        "agent_suggestions": [],
    }


def test_build_deferred_revenue_release_proposal_values_current_period() -> None:
    proposals = build_deferred_revenue_release_proposals(_deps(_base_tables()), "2026-06")

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.proposal_type == "deferred_revenue_release"
    assert proposal.period == "2026-06"
    assert proposal.currency == "USD"
    assert proposal.deferred_release_amount == "1000.00"
    assert proposal.confidence == 0.72
    assert proposal.journal_entry["entry_date"] == "2026-06-30"
    assert proposal.journal_entry["lines"][0]["direction"] == "DR"
    assert proposal.journal_entry["lines"][0]["account_id"] == "deferred-account"
    assert proposal.journal_entry["lines"][1]["direction"] == "CR"
    assert proposal.journal_entry["lines"][1]["account_id"] == "revenue-account"


def test_build_deferred_revenue_release_returns_empty_without_deferred_account() -> None:
    tables = _base_tables()
    tables["accounts"] = [
        {
            "tenant_id": TENANT_ID,
            "id": "revenue-account",
            "code": "4000",
            "deleted_at": None,
        }
    ]

    proposals = build_deferred_revenue_release_proposals(_deps(tables), "2026-06")

    assert proposals == []


def test_build_deferred_revenue_release_raises_for_missing_revenue_account() -> None:
    tables = _base_tables()
    tables["accounts"] = [
        {
            "tenant_id": TENANT_ID,
            "id": "deferred-account",
            "code": "2200",
            "deleted_at": None,
        }
    ]

    with pytest.raises(RevenueRecognitionProposalError) as exc_info:
        build_deferred_revenue_release_proposals(_deps(tables), "2026-06")

    assert "4000" in str(exc_info.value)


@pytest.mark.asyncio
async def test_write_deferred_revenue_release_suggestions_writes_l2_hitl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    async def _fake_write(*args: Any, **kwargs: Any) -> dict:
        calls.append({"deps": args[0], **kwargs})
        return {"id": "suggestion-001"}

    monkeypatch.setattr(
        "app.agents.revenue_recognition_agent.write_agent_suggestion",
        _fake_write,
    )

    result = await write_deferred_revenue_release_suggestions(
        _deps(_base_tables()),
        "2026-06",
    )

    assert result["created_count"] == 1
    assert result["suggestion_ids"] == ["suggestion-001"]
    assert calls[0]["agent_name"] == "revenue_recognition_agent"
    assert calls[0]["action_type"] == "draft_journal"
    assert calls[0]["autonomy_level"] == 2
    assert calls[0]["output"]["deferred_release_amount"] == "1000.00"


@pytest.mark.asyncio
async def test_write_deferred_revenue_release_suggestions_skips_duplicate() -> None:
    tables = _base_tables()
    tables["agent_suggestions"] = [
        {
            "tenant_id": TENANT_ID,
            "agent_name": "revenue_recognition_agent",
            "action_type": "draft_journal",
            "status": "pending",
            "output_snapshot": {
                "proposal_type": "deferred_revenue_release",
                "period": "2026-06",
                "currency": "USD",
            },
        }
    ]

    result = await write_deferred_revenue_release_suggestions(_deps(tables), "2026-06")

    assert result["created_count"] == 0
    assert result["skipped_duplicates"] == 1
