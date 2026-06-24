"""Workflow-run coverage for scheduled agent workers."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest

pytestmark = pytest.mark.unit


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _WorkflowDb, table: str, rows: list[dict[str, Any]]) -> None:
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

    def in_(self, key: str, values: list[Any] | tuple[Any, ...]) -> _Query:
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

    def lt(self, key: str, value: Any) -> _Query:
        self.rows = [row for row in self.rows if str(row.get(key) or "") < str(value)]
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
            return _Result(self.rows)
        rows = self.rows[: self.limit_count] if self.limit_count is not None else self.rows
        return _Result(rows)


class _WorkflowDb:
    def __init__(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        self.tables = tables

    def table(self, name: str) -> _Query:
        self.tables.setdefault(name, [])
        return _Query(self, name, self.tables[name])


def test_project_health_worker_records_waiting_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.workers import project_health_worker as worker

    db = _WorkflowDb(
        {
            "tenants": [{"id": "tenant-1", "status": "active"}],
            "projects": [
                {
                    "id": "project-1",
                    "tenant_id": "tenant-1",
                    "status": "active",
                    "deleted_at": None,
                    "name": "Launch",
                }
            ],
            "agent_workflow_runs": [],
        }
    )

    async def _run_tenant_checks(projects: list[dict[str, Any]], _deps: Any) -> int:
        assert [project["id"] for project in projects] == ["project-1"]
        return 2

    monkeypatch.setattr(worker, "get_service_role_client", lambda: db)
    monkeypatch.setattr(worker, "_run_tenant_checks", _run_tenant_checks)

    result = worker.run_project_health_checks.func(0)

    assert result == {"total_alerts_created": 2, "tenants_checked": 1}
    workflow = db.tables["agent_workflow_runs"][0]
    assert workflow["workflow_name"] == "daily_project_health_checks"
    assert workflow["owner_agent_name"] == "project_health_agent"
    assert workflow["status"] == "waiting_on_human"
    assert workflow["current_step"] == "hitl_review"
    assert workflow["state_snapshot"] == {
        "project_count": 1,
        "alerts_created": 2,
    }


@pytest.mark.asyncio
async def test_collections_worker_records_hitl_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.workers import collections as worker

    db = _WorkflowDb(
        {
            "tenants": [
                {"id": "tenant-1", "name": "Aethos", "status": "active"},
            ],
            "invoices": [
                {
                    "id": "invoice-1",
                    "tenant_id": "tenant-1",
                    "status": "overdue",
                    "invoice_number": "INV-001",
                    "total": "1250.00",
                    "currency": "USD",
                    "due_date": (date.today() - timedelta(days=12)).isoformat(),
                    "client_id": "client-1",
                    "stripe_payment_link_url": "",
                }
            ],
            "clients": [
                {
                    "id": "client-1",
                    "name": "Acme",
                    "billing_address": {"email": "finance@acme.test"},
                }
            ],
            "collections_policies": [],
            "agent_autonomy_settings": [],
            "agent_suggestions": [],
            "agent_workflow_runs": [],
        }
    )

    class _Resend:
        def send_email(self, *_args: Any, **_kwargs: Any) -> dict[str, str]:
            raise AssertionError("L2 collections reminder should not auto-send")

    async def _write_agent_suggestion(*_args: Any, **_kwargs: Any) -> dict[str, str]:
        return {"id": "suggestion-1"}

    monkeypatch.setattr(worker, "create_client", lambda *_args: db)
    monkeypatch.setattr(worker, "ResendService", lambda: _Resend())
    monkeypatch.setattr(worker, "write_agent_suggestion", _write_agent_suggestion)

    result = await worker.collections_worker.func(0)

    assert result == {
        "sent": 0,
        "hitl_queued": 1,
        "skipped_duplicates": 0,
        "skipped_policy": 0,
    }
    workflow = db.tables["agent_workflow_runs"][0]
    assert workflow["workflow_name"] == "daily_collections"
    assert workflow["owner_agent_name"] == "collections_agent"
    assert workflow["status"] == "waiting_on_human"
    assert workflow["current_step"] == "hitl_review"
    assert workflow["state_snapshot"] == {
        "overdue_invoices": 1,
        "sent": 0,
        "hitl_queued": 1,
        "skipped_duplicates": 0,
        "skipped_policy": 0,
        "invoice_errors": 0,
    }


def test_finance_ops_manager_worker_is_registered() -> None:
    from procrastinate.tasks import Task

    from app.workers.finance_ops_manager_worker import run_scheduled_finance_ops_manager

    assert isinstance(run_scheduled_finance_ops_manager, Task)


@pytest.mark.asyncio
async def test_scheduled_finance_ops_manager_creates_review_plan_and_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.workers import finance_ops_manager_worker as worker

    db = _WorkflowDb(
        {
            "tenants": [{"id": "tenant-1", "status": "active"}],
            "finance_ops_schedules": [
                {
                    "tenant_id": "tenant-1",
                    "is_enabled": True,
                    "cadence": "daily",
                    "run_hour_utc": 7,
                    "run_weekday_utc": 0,
                    "period_mode": "current_month",
                    "lookback_limit": 10,
                    "stale_after_hours": 24,
                    "high_risk_stale_after_hours": 4,
                    "escalation_enabled": True,
                }
            ],
            "tenant_users": [
                {
                    "tenant_id": "tenant-1",
                    "user_id": "admin-1",
                    "role": "admin",
                    "deleted_at": None,
                }
            ],
            "agent_suggestions": [],
            "hitl_tasks": [],
            "agent_workflow_runs": [],
        }
    )

    async def _build_plan(
        _db: Any,
        *,
        tenant_id: str,
        tool_input: dict[str, Any],
    ) -> dict[str, Any]:
        assert tenant_id == "tenant-1"
        assert tool_input == {"period": "2026-06", "limit": 10}
        return {
            "finance_ops_action_plan": True,
            "plan_id": "plan-1",
            "period": "2026-06",
            "action_count": 1,
            "action_items": [],
        }

    monkeypatch.setattr(worker, "_build_finance_ops_action_plan", _build_plan)

    result = await worker._run_scheduled_finance_ops_manager(
        db,
        as_of=datetime(2026, 6, 24, 7, 5, tzinfo=UTC),
    )

    assert result["tenants_due"] == 1
    assert result["plans_created"] == 1
    assert result["escalations_created"] == 0
    suggestion = db.tables["agent_suggestions"][0]
    assert suggestion["agent_name"] == "copilot_agent"
    assert suggestion["action_type"] == "copilot_create_finance_ops_action_plan"
    assert suggestion["output_snapshot"]["scheduled_run"] is True
    assert suggestion["output_snapshot"]["source_schedule_key"] == (
        "tenant-1:daily:2026-06-24"
    )
    task = db.tables["hitl_tasks"][0]
    assert task["kind"] == "copilot_create_finance_ops_action_plan"
    assert task["status"] == "open"
    workflow = db.tables["agent_workflow_runs"][0]
    assert workflow["workflow_name"] == "scheduled_finance_ops_manager"
    assert workflow["owner_agent_name"] == "finance_ops_manager"
    assert workflow["status"] == "waiting_on_human"
    assert workflow["current_step"] == "hitl_review"


@pytest.mark.asyncio
async def test_scheduled_finance_ops_manager_suppresses_duplicate_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.workers import finance_ops_manager_worker as worker

    db = _WorkflowDb(
        {
            "tenants": [{"id": "tenant-1", "status": "active"}],
            "finance_ops_schedules": [],
            "tenant_users": [],
            "agent_suggestions": [],
            "hitl_tasks": [
                {
                    "id": "task-existing",
                    "tenant_id": "tenant-1",
                    "kind": "copilot_create_finance_ops_action_plan",
                    "priority": "high",
                    "title": "Existing plan",
                    "payload": {
                        "scheduled_run": True,
                        "source_schedule_key": "tenant-1:daily:2026-06-24",
                    },
                    "status": "open",
                    "created_at": "2026-06-24T07:00:00+00:00",
                }
            ],
            "agent_workflow_runs": [],
        }
    )

    async def _build_plan(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("duplicate scheduled plan should suppress rebuild")

    monkeypatch.setattr(worker, "_build_finance_ops_action_plan", _build_plan)

    result = await worker._run_scheduled_finance_ops_manager(
        db,
        as_of=datetime(2026, 6, 24, 7, 5, tzinfo=UTC),
    )

    assert result["plans_created"] == 0
    assert result["plans_skipped_duplicate"] == 1
    assert len(db.tables["agent_suggestions"]) == 0
    workflow = db.tables["agent_workflow_runs"][0]
    assert workflow["status"] == "succeeded"
    assert workflow["state_snapshot"]["plan_skipped_duplicate"] is True


def test_finance_ops_manager_escalates_stale_high_risk_without_payload_copy() -> None:
    from app.workers import finance_ops_manager_worker as worker

    db = _WorkflowDb(
        {
            "agent_suggestions": [],
            "hitl_tasks": [
                {
                    "id": "task-pay",
                    "tenant_id": "tenant-1",
                    "kind": "create_bill_payment_batch",
                    "priority": "high",
                    "title": "Review $60k vendor payment",
                    "payload": {
                        "risk_class": "write_money_out",
                        "total_amount": "60000.00",
                        "secret_field": "do-not-copy",
                    },
                    "status": "open",
                    "created_at": "2026-06-24T00:00:00+00:00",
                }
            ],
            "tenant_users": [
                {
                    "tenant_id": "tenant-1",
                    "user_id": "owner-1",
                    "role": "owner",
                    "deleted_at": None,
                },
                {
                    "tenant_id": "tenant-1",
                    "user_id": "manager-1",
                    "role": "manager",
                    "deleted_at": None,
                },
            ],
        }
    )
    schedule = {
        **worker.DEFAULT_SCHEDULE,
        "tenant_id": "tenant-1",
        "high_risk_stale_after_hours": 4,
        "stale_after_hours": 24,
    }

    created = worker._create_escalation_tasks(
        db,
        tenant_id="tenant-1",
        schedule=schedule,
        as_of=datetime(2026, 6, 24, 7, 5, tzinfo=UTC),
    )

    assert created == 1
    escalation_suggestion = db.tables["agent_suggestions"][0]
    assert escalation_suggestion["agent_name"] == "finance_ops_manager"
    assert escalation_suggestion["action_type"] == "finance_ops_escalation"
    output = escalation_suggestion["output_snapshot"]
    assert output["source_task_id"] == "task-pay"
    assert output["required_approval_role"] == "owner"
    assert output["payload_summary"] == {
        "risk_class": "write_money_out",
        "total_amount": "60000.00",
    }
    assert "secret_field" not in output
    escalation_task = db.tables["hitl_tasks"][1]
    assert escalation_task["kind"] == "finance_ops_escalation"
    assert escalation_task["priority"] == "critical"
    assert escalation_task["assigned_to"] == "owner-1"
