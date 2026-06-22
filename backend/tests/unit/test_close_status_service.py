"""Unit tests for derived financial close status."""

from __future__ import annotations

from typing import Any

import pytest

from app.services.close_status_service import CloseStatusService, close_review_blocker_detail

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-close-status-001"


class _Result:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _NotFilter:
    def __init__(self, query: _Query) -> None:
        self._query = query

    def is_(self, field: str, value: str) -> _Query:
        self._query._filters.append(("not_is", field, value))
        return self._query


class _Query:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self._filters: list[tuple[str, str, Any]] = []
        self.not_ = _NotFilter(self)

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
            if op == "not_is" and value == "null" and current is None:
                return False
        return True


class _Db:
    def __init__(self, tables: dict[str, list[dict]]) -> None:
        self.tables = tables

    def table(self, name: str) -> _Query:
        return _Query(self.tables.get(name, []))


def _journal_line(direction: str, amount: str, code: str, period: str) -> dict:
    account_names = {
        "1200": ("Accounts Receivable", "asset"),
        "4000": ("Revenue", "revenue"),
    }
    name, account_type = account_names[code]
    return {
        "tenant_id": TENANT_ID,
        "direction": direction,
        "base_amount": amount,
        "journal_entries": {
            "period": period,
            "posted_at": f"{period}-30T00:00:00+00:00",
        },
        "accounts": {
            "code": code,
            "name": name,
            "account_type": account_type,
        },
    }


def _base_tables() -> dict[str, list[dict]]:
    return {
        "invoices": [],
        "bills": [],
        "journal_entries": [],
        "journal_lines": [
            _journal_line("DR", "100.00", "1200", "2026-06"),
            _journal_line("CR", "100.00", "4000", "2026-06"),
        ],
        "period_locks": [],
        "agent_suggestions": [],
    }


def test_close_status_ready_when_reconciled_and_no_pending_reviews() -> None:
    result = CloseStatusService(_Db(_base_tables()), TENANT_ID).get_status("2026-06")  # type: ignore[arg-type]

    assert result.status == "ready"
    assert result.ready_to_lock is True
    assert result.lock_blockers == []
    checklist = {item.code: item for item in result.checklist}
    assert checklist["subledger_reconciliation"].status == "complete"
    assert checklist["trial_balance"].status == "complete"
    assert checklist["close_reviews"].status == "complete"
    assert checklist["period_lock"].status == "pending"


def test_close_status_blocks_for_pending_close_review() -> None:
    tables = _base_tables()
    tables["agent_suggestions"] = [
        {
            "tenant_id": TENANT_ID,
            "id": "suggestion-001",
            "agent_name": "accrual_agent",
            "action_type": "draft_journal",
            "status": "pending",
            "output_snapshot": {
                "period": "2026-06",
                "currency": "USD",
                "wip_value": "2500.00",
            },
        }
    ]

    result = CloseStatusService(_Db(tables), TENANT_ID).get_status("2026-06")  # type: ignore[arg-type]

    assert result.status == "blocked"
    assert result.ready_to_lock is False
    assert result.lock_blockers == ["close_reviews"]
    assert result.pending_reviews[0].summary == "Review USD WIP accrual proposal for 2500.00."
    assert close_review_blocker_detail("2026-06", result.pending_reviews)["code"] == (
        "close_review_pending"
    )


def test_close_status_blocks_for_pending_revenue_recognition_review() -> None:
    tables = _base_tables()
    tables["agent_suggestions"] = [
        {
            "tenant_id": TENANT_ID,
            "id": "suggestion-revrec-001",
            "agent_name": "revenue_recognition_agent",
            "action_type": "draft_journal",
            "status": "pending",
            "output_snapshot": {
                "proposal_type": "deferred_revenue_release",
                "period": "2026-06",
                "currency": "USD",
                "deferred_release_amount": "1000.00",
            },
        }
    ]

    result = CloseStatusService(_Db(tables), TENANT_ID).get_status("2026-06")  # type: ignore[arg-type]

    assert result.status == "blocked"
    assert result.lock_blockers == ["close_reviews"]
    assert result.pending_reviews[0].summary == (
        "Review USD deferred revenue release proposal for 1000.00."
    )


def test_close_status_marks_already_locked_period() -> None:
    tables = _base_tables()
    tables["period_locks"] = [
        {
            "tenant_id": TENANT_ID,
            "period": "2026-06",
            "locked_at": "2026-06-30T23:00:00+00:00",
            "locked_by": "user-001",
        }
    ]

    result = CloseStatusService(_Db(tables), TENANT_ID).get_status("2026-06")  # type: ignore[arg-type]

    assert result.status == "locked"
    assert result.locked is True
    assert result.ready_to_lock is False
    assert result.locked_by == "user-001"
    assert {item.code: item.status for item in result.checklist}["period_lock"] == "complete"
