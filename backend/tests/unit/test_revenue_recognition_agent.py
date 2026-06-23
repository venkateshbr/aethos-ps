"""Unit tests for deferred revenue release proposal generation."""

from __future__ import annotations

from typing import Any

import pytest

from app.agents.base import AgentDeps
from app.agents.revenue_recognition_agent import (
    RevenueRecognitionProposalError,
    build_deferred_revenue_release_proposals,
    build_milestone_revenue_recognition_proposals,
    write_deferred_revenue_release_suggestions,
    write_milestone_revenue_recognition_suggestions,
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
            if op == "gte" and (current is None or str(current) < str(value)):
                return False
            if op == "lte" and (current is None or str(current) > str(value)):
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
        "project_phases": [
            {
                "id": "phase-discovery",
                "tenant_id": TENANT_ID,
                "project_id": "project-001",
                "name": "Discovery sign-off",
                "status": "completed",
                "end_date": "2026-06-18",
                "budget": "9000.00",
                "revenue_recognition_amount": "12500.00",
                "percent_complete": "100",
                "deleted_at": None,
            },
            {
                "id": "phase-july",
                "tenant_id": TENANT_ID,
                "project_id": "project-001",
                "name": "Future milestone",
                "status": "completed",
                "end_date": "2026-07-02",
                "budget": "5000.00",
                "revenue_recognition_amount": "5000.00",
                "percent_complete": "100",
                "deleted_at": None,
            },
            {
                "id": "phase-non-milestone",
                "tenant_id": TENANT_ID,
                "project_id": "project-002",
                "name": "Fixed-fee completion",
                "status": "completed",
                "end_date": "2026-06-20",
                "budget": "7000.00",
                "revenue_recognition_amount": "7000.00",
                "percent_complete": "100",
                "deleted_at": None,
            },
        ],
        "projects": [
            {
                "id": "project-001",
                "tenant_id": TENANT_ID,
                "engagement_id": "eng-milestone",
                "name": "ERP rollout",
                "currency": "USD",
                "deleted_at": None,
            },
            {
                "id": "project-002",
                "tenant_id": TENANT_ID,
                "engagement_id": "eng-fixed-fee",
                "name": "Fixed scope",
                "currency": "USD",
                "deleted_at": None,
            },
        ],
        "engagements": [
            {
                "id": "eng-milestone",
                "tenant_id": TENANT_ID,
                "name": "ERP transformation",
                "billing_arrangement": "milestone",
                "currency": "USD",
                "deleted_at": None,
            },
            {
                "id": "eng-fixed-fee",
                "tenant_id": TENANT_ID,
                "name": "Fixed fee advisory",
                "billing_arrangement": "fixed_fee",
                "currency": "USD",
                "deleted_at": None,
            },
        ],
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


def test_build_milestone_revenue_recognition_proposal_values_completed_phase() -> None:
    proposals = build_milestone_revenue_recognition_proposals(
        _deps(_base_tables()),
        "2026-06",
    )

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.proposal_type == "milestone_revenue_recognition"
    assert proposal.period == "2026-06"
    assert proposal.phase_id == "phase-discovery"
    assert proposal.project_id == "project-001"
    assert proposal.engagement_id == "eng-milestone"
    assert proposal.recognition_amount == "12500.00"
    assert proposal.amount_source == "revenue_recognition_amount"
    assert proposal.confidence == 0.86
    assert proposal.journal_entry["entry_date"] == "2026-06-30"
    assert proposal.journal_entry["lines"][0]["direction"] == "DR"
    assert proposal.journal_entry["lines"][0]["account_id"] == "deferred-account"
    assert proposal.journal_entry["lines"][1]["direction"] == "CR"
    assert proposal.journal_entry["lines"][1]["account_id"] == "revenue-account"


def test_build_milestone_revenue_recognition_uses_budget_legacy_fallback() -> None:
    tables = _base_tables()
    tables["project_phases"][0]["revenue_recognition_amount"] = None

    proposals = build_milestone_revenue_recognition_proposals(
        _deps(tables),
        "2026-06",
    )

    assert len(proposals) == 1
    assert proposals[0].recognition_amount == "9000.00"
    assert proposals[0].amount_source == "phase_budget"
    assert proposals[0].confidence == 0.68


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
async def test_write_milestone_revenue_recognition_suggestions_writes_l2_hitl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    async def _fake_write(*args: Any, **kwargs: Any) -> dict:
        calls.append({"deps": args[0], **kwargs})
        return {"id": "suggestion-milestone-001"}

    monkeypatch.setattr(
        "app.agents.revenue_recognition_agent.write_agent_suggestion",
        _fake_write,
    )

    result = await write_milestone_revenue_recognition_suggestions(
        _deps(_base_tables()),
        "2026-06",
    )

    assert result["created_count"] == 1
    assert result["suggestion_ids"] == ["suggestion-milestone-001"]
    assert calls[0]["agent_name"] == "revenue_recognition_agent"
    assert calls[0]["action_type"] == "draft_journal"
    assert calls[0]["related_entity_type"] == "project_phase"
    assert calls[0]["related_entity_id"] == "phase-discovery"
    assert calls[0]["output"]["recognition_amount"] == "12500.00"


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


@pytest.mark.asyncio
async def test_write_milestone_revenue_recognition_suggestions_skips_duplicate() -> None:
    tables = _base_tables()
    tables["agent_suggestions"] = [
        {
            "tenant_id": TENANT_ID,
            "agent_name": "revenue_recognition_agent",
            "action_type": "draft_journal",
            "status": "approved",
            "output_snapshot": {
                "proposal_type": "milestone_revenue_recognition",
                "period": "2026-06",
                "phase_id": "phase-discovery",
            },
        }
    ]

    result = await write_milestone_revenue_recognition_suggestions(
        _deps(tables),
        "2026-06",
    )

    assert result["created_count"] == 0
    assert result["skipped_duplicates"] == 1
