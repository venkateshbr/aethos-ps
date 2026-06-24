"""Unit tests for the time-entry reminder agent and worker."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from app.agents.time_entry_agent import (
    draft_time_entry_reminder,
    expected_weekly_hours,
)

pytestmark = pytest.mark.unit


def test_expected_weekly_hours_uses_availability_and_utilization_target() -> None:
    assert expected_weekly_hours(
        {
            "available_hours_per_week": "40",
            "target_billable_utilization_pct": "75",
        }
    ) == Decimal("30.00")


def test_draft_time_entry_reminder_requires_missing_hour_threshold() -> None:
    draft = draft_time_entry_reminder(
        employee={
            "id": "emp-1",
            "first_name": "Riya",
            "last_name": "Shah",
            "email": "riya@example.com",
            "available_hours_per_week": "40",
            "target_billable_utilization_pct": "100",
        },
        projects=[
            {
                "project_id": "proj-1",
                "project_code": "ACME-01",
                "project_name": "Acme Advisory",
                "role": "Consultant",
            }
        ],
        logged_hours=Decimal("40"),
        week_start=date(2026, 6, 22),
        week_end=date(2026, 6, 28),
        tenant_name="Aethos",
    )

    assert draft is None


def test_draft_time_entry_reminder_contains_project_context() -> None:
    draft = draft_time_entry_reminder(
        employee={
            "id": "emp-1",
            "first_name": "Riya",
            "last_name": "Shah",
            "email": "riya@example.com",
            "available_hours_per_week": "40",
            "target_billable_utilization_pct": "75",
        },
        projects=[
            {
                "project_id": "proj-1",
                "project_code": "ACME-01",
                "project_name": "Acme Advisory",
                "role": "Consultant",
            }
        ],
        logged_hours=Decimal("20"),
        week_start=date(2026, 6, 22),
        week_end=date(2026, 6, 28),
        tenant_name="Aethos",
    )

    assert draft is not None
    assert draft.employee_name == "Riya Shah"
    assert draft.expected_hours == Decimal("30.00")
    assert draft.logged_hours == Decimal("20.00")
    assert draft.missing_hours == Decimal("10.00")
    assert draft.active_projects[0].project_code == "ACME-01"
    assert "ACME-01" in draft.body_html


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _FakeDb, table: str, rows: list[dict[str, Any]]) -> None:
        self.db = db
        self.table = table
        self.rows = list(rows)
        self.update_payload: dict[str, Any] | None = None
        self.limit_count: int | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self.rows = [row for row in self.rows if row.get(key) == value]
        return self

    def in_(self, key: str, values: list[Any]) -> _Query:
        value_set = {str(value) for value in values}
        self.rows = [row for row in self.rows if str(row.get(key)) in value_set]
        return self

    def is_(self, key: str, value: Any) -> _Query:
        if value == "null":
            self.rows = [row for row in self.rows if row.get(key) is None]
        return self

    def gte(self, key: str, value: Any) -> _Query:
        self.rows = [row for row in self.rows if str(row.get(key) or "") >= str(value)]
        return self

    def lte(self, key: str, value: Any) -> _Query:
        self.rows = [row for row in self.rows if str(row.get(key) or "") <= str(value)]
        return self

    def limit(self, count: int) -> _Query:
        self.limit_count = count
        return self

    def insert(self, payload: dict[str, Any]) -> _Query:
        row = {"id": f"{self.table}-{len(self.db.tables[self.table]) + 1}", **payload}
        self.db.tables[self.table].append(row)
        self.rows = [row]
        return self

    def update(self, payload: dict[str, Any]) -> _Query:
        self.update_payload = payload
        return self

    def execute(self) -> _Result:
        if self.update_payload is not None:
            for row in self.rows:
                row.update(self.update_payload)
            return _Result(deepcopy(self.rows))
        rows = self.rows[: self.limit_count] if self.limit_count is not None else self.rows
        return _Result(deepcopy(rows))


class _FakeDb:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "employees": [
                {
                    "id": "emp-1",
                    "tenant_id": "tenant-1",
                    "first_name": "Riya",
                    "last_name": "Shah",
                    "email": "riya@example.com",
                    "available_hours_per_week": "40",
                    "target_billable_utilization_pct": "75",
                    "status": "active",
                    "deleted_at": None,
                }
            ],
            "project_assignments": [
                {
                    "id": "assignment-1",
                    "tenant_id": "tenant-1",
                    "employee_id": "emp-1",
                    "project_id": "proj-1",
                    "role": "Consultant",
                    "start_date": "2026-01-01",
                    "end_date": None,
                }
            ],
            "projects": [
                {
                    "id": "proj-1",
                    "tenant_id": "tenant-1",
                    "code": "ACME-01",
                    "name": "Acme Advisory",
                    "status": "active",
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "deleted_at": None,
                }
            ],
            "time_entries": [
                {
                    "tenant_id": "tenant-1",
                    "employee_id": "emp-1",
                    "project_id": "proj-1",
                    "date": "2026-06-22",
                    "hours": "8",
                    "status": "approved",
                    "deleted_at": None,
                }
            ],
            "agent_suggestions": [],
            "hitl_tasks": [],
            "agent_autonomy_settings": [],
            "agent_workflow_runs": [],
        }

    def table(self, name: str) -> _Query:
        self.tables.setdefault(name, [])
        return _Query(self, name, self.tables[name])


def test_build_weekly_reminder_drafts_uses_assignments_and_logged_hours() -> None:
    from app.workers.time_entry_reminder_worker import _build_weekly_reminder_drafts

    drafts = _build_weekly_reminder_drafts(
        _FakeDb(),
        tenant_id="tenant-1",
        tenant_name="Aethos",
        week_start=date(2026, 6, 22),
        week_end=date(2026, 6, 28),
    )

    assert len(drafts) == 1
    assert drafts[0].employee_id == "emp-1"
    assert drafts[0].logged_hours == Decimal("8.00")
    assert drafts[0].missing_hours == Decimal("22.00")


def test_recent_time_entry_reminder_matches_employee_and_week() -> None:
    from app.workers.time_entry_reminder_worker import _recent_time_entry_reminder_exists

    db = _FakeDb()
    db.tables["agent_suggestions"].append(
        {
            "tenant_id": "tenant-1",
            "agent_name": "time_entry_agent",
            "action_type": "send_time_entry_reminder",
            "status": "pending",
            "related_entity_id": "emp-1",
            "output_snapshot": {"employee_id": "emp-1", "week_start": "2026-06-22"},
        }
    )

    assert _recent_time_entry_reminder_exists(
        db,
        tenant_id="tenant-1",
        employee_id="emp-1",
        week_start="2026-06-22",
    )
    assert not _recent_time_entry_reminder_exists(
        db,
        tenant_id="tenant-1",
        employee_id="emp-1",
        week_start="2026-06-29",
    )


@pytest.mark.asyncio
async def test_process_tenant_week_queues_hitl_and_updates_workflow() -> None:
    from app.workers.time_entry_reminder_worker import _process_tenant_week

    db = _FakeDb()

    class _Resend:
        def send_email(self, _to: str, _subject: str, _body_html: str) -> dict:
            raise AssertionError("L2 reminder should not auto-send")

    result = await _process_tenant_week(
        db,
        resend=_Resend(),  # type: ignore[arg-type]
        tenant_id="tenant-1",
        tenant_name="Aethos",
        as_of=date(2026, 6, 26),
    )

    assert result["hitl_queued"] == 1
    assert db.tables["agent_suggestions"][0]["agent_name"] == "time_entry_agent"
    assert db.tables["agent_suggestions"][0]["action_type"] == "send_time_entry_reminder"
    assert db.tables["hitl_tasks"][0]["kind"] == "send_time_entry_reminder"
    assert db.tables["agent_workflow_runs"][0]["status"] == "waiting_on_human"
    assert db.tables["agent_workflow_runs"][0]["current_step"] == "hitl_review"


@pytest.mark.asyncio
async def test_inbox_materialises_time_entry_reminder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.inbox_service import InboxService

    sent: list[tuple[str, str, str]] = []

    class _Resend:
        def send_email(self, to: str, subject: str, body_html: str) -> dict:
            sent.append((to, subject, body_html))
            return {"id": "email-1"}

    monkeypatch.setattr("app.services.resend_service.ResendService", lambda: _Resend())

    svc = InboxService.__new__(InboxService)
    result = await svc._materialise_time_entry_reminder(
        {
            "employee_id": "emp-1",
            "employee_email": "riya@example.com",
            "subject": "Time reminder",
            "body_html": "<p>Please log time</p>",
        }
    )

    assert result == {
        "entity_type": "time_entry_reminder",
        "entity_id": "emp-1",
        "send_status": "sent",
    }
    assert sent == [("riya@example.com", "Time reminder", "<p>Please log time</p>")]
