"""Workflow-run coverage for scheduled agent workers."""

from __future__ import annotations

from datetime import date, timedelta
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
