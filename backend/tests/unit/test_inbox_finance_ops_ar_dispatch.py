"""Finance Ops AR child approval integration at the Inbox service boundary."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import date, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services.inbox_service import InboxService

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-ar-approval"
OWNER_ID = "00000000-0000-0000-0000-000000000001"
PARENT_SUGGESTION_ID = "parent-suggestion-1"
PARENT_TASK_ID = "parent-task-1"
INVOICE_ID = "00000000-0000-0000-0000-000000000101"
CLIENT_ID = "00000000-0000-0000-0000-000000000201"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _StatefulDb, table: str) -> None:
        self._db = db
        self._table = table
        self._filters: list[tuple[str, str, Any]] = []
        self._operation = "select"
        self._payload: dict[str, Any] = {}
        self._limit: int | None = None
        self._order_key: str | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._filters.append(("eq", key, value))
        return self

    def in_(self, key: str, values: list[Any]) -> _Query:
        self._filters.append(("in", key, list(values)))
        return self

    def is_(self, key: str, value: Any) -> _Query:
        self._filters.append(("eq", key, None if value == "null" else value))
        return self

    def lt(self, key: str, value: Any) -> _Query:
        self._filters.append(("lt", key, value))
        return self

    def gte(self, key: str, value: Any) -> _Query:
        self._filters.append(("gte", key, value))
        return self

    def limit(self, value: int) -> _Query:
        self._limit = value
        return self

    def order(self, key: str, **_kwargs: Any) -> _Query:
        self._order_key = key
        return self

    def insert(self, payload: dict[str, Any]) -> _Query:
        self._operation = "insert"
        self._payload = deepcopy(payload)
        return self

    def update(self, payload: dict[str, Any]) -> _Query:
        self._operation = "update"
        self._payload = deepcopy(payload)
        return self

    def execute(self) -> _Result:
        if self._operation == "insert":
            row = deepcopy(self._payload)
            row.setdefault(
                "id",
                f"{self._table}-{len(self._db.tables.setdefault(self._table, [])) + 1}",
            )
            self._db.tables[self._table].append(row)
            self._db.inserts.setdefault(self._table, []).append(deepcopy(row))
            return _Result([deepcopy(row)])

        rows = self._filtered_rows()
        if self._operation == "update":
            for row in rows:
                row.update(deepcopy(self._payload))
            self._db.updates.setdefault(self._table, []).append(deepcopy(self._payload))
            return _Result(deepcopy(rows))

        if self._order_key is not None:
            rows.sort(key=lambda row: str(row.get(self._order_key) or ""))
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Result(deepcopy(rows))

    def _filtered_rows(self) -> list[dict[str, Any]]:
        rows = list(self._db.tables.setdefault(self._table, []))
        for operation, key, value in self._filters:
            if operation == "eq":
                rows = [row for row in rows if row.get(key) == value]
            elif operation == "in":
                rows = [row for row in rows if row.get(key) in value]
            elif operation == "lt":
                rows = [row for row in rows if row.get(key) < value]
            elif operation == "gte":
                rows = [row for row in rows if row.get(key) >= value]
        return rows


class _RpcQuery:
    def __init__(self, db: _StatefulDb, params: dict[str, Any]) -> None:
        self._db = db
        self._params = params

    def execute(self) -> _Result:
        row = {
            "id": f"financial-event-{len(self._db.tables['financial_events']) + 1}",
            "tenant_id": self._params["p_tenant_id"],
            "event_type": self._params["p_event_type"],
            "entity_type": self._params["p_entity_type"],
            "entity_id": self._params["p_entity_id"],
            "action": self._params["p_action"],
        }
        self._db.tables["financial_events"].append(row)
        return _Result([deepcopy(row)])


class _StatefulDb:
    def __init__(self, *, fail_invoice_read: bool = False) -> None:
        due_date = (date.today() - timedelta(days=45)).isoformat()
        action_payload = {
            "finance_ops_action_item": True,
            "parent_plan_id": "finance-ops-plan-1",
            "period": date.today().strftime("%Y-%m"),
            "action_item_id": "finance-ops-plan-1-ar",
            "domain": "ar",
            "suggested_agent": "collections_agent",
            "suggested_tool": "send_email",
            "risk_class": "write_money_in",
            "requires_inbox_approval": True,
            "dispatch_tool": "draft_collection_reminders",
            "dispatch_input": {
                "minimum_days_overdue": 1,
                "limit": 10,
                "tone": "auto",
            },
            "requested_by_user_id": OWNER_ID,
        }
        parent_suggestion = {
            "id": PARENT_SUGGESTION_ID,
            "tenant_id": TENANT_ID,
            "agent_name": "collections_agent",
            "action_type": "finance_ops_action_item",
            "output_snapshot": action_payload,
            "confidence": "0.00",
            "status": "pending",
        }
        self.tables: dict[str, list[dict[str, Any]]] = {
            "tenant_approval_policies": [],
            "tenant_users": [
                {
                    "tenant_id": TENANT_ID,
                    "user_id": OWNER_ID,
                    "role": "owner",
                    "deleted_at": None,
                }
            ],
            "tenant_user_effective_privileges": [],
            "agent_autonomy_settings": [],
            "agent_suggestions": [parent_suggestion],
            "hitl_tasks": [
                {
                    "id": PARENT_TASK_ID,
                    "tenant_id": TENANT_ID,
                    "agent_suggestion_id": PARENT_SUGGESTION_ID,
                    "kind": "finance_ops_action_item",
                    "priority": "high",
                    "title": "Review AR plan item",
                    "description": "Stage a collections reminder.",
                    "payload": action_payload,
                    "status": "open",
                    "created_at": "2026-07-11T00:00:00+00:00",
                    "updated_at": "2026-07-11T00:00:00+00:00",
                    "agent_suggestions": parent_suggestion,
                }
            ],
            "invoices": [
                {
                    "id": INVOICE_ID,
                    "tenant_id": TENANT_ID,
                    "invoice_number": "INV-AR-TEST-1",
                    "total": "1250.00",
                    "currency": "USD",
                    "due_date": due_date,
                    "client_id": CLIENT_ID,
                    "stripe_payment_link_url": "",
                    "status": "sent",
                    "deleted_at": None,
                }
            ],
            "clients": [
                {
                    "id": CLIENT_ID,
                    "tenant_id": TENANT_ID,
                    "name": "AR Approval Test Client",
                    "billing_email": "collections@example.test",
                    "billing_address": {},
                }
            ],
            "tenants": [{"id": TENANT_ID, "name": "AR Approval Test Firm"}],
            "collections_policies": [],
            "agent_runs": [],
            "agent_tool_invocations": [],
            "financial_events": [],
        }
        self.inserts: dict[str, list[dict[str, Any]]] = {}
        self.updates: dict[str, list[dict[str, Any]]] = {}
        self.table_calls: list[str] = []
        self.fail_invoice_read = fail_invoice_read

    def table(self, name: str) -> _Query:
        self.table_calls.append(name)
        if name == "invoices" and self.fail_invoice_read:
            raise RuntimeError("invoice read unavailable")
        return _Query(self, name)

    def rpc(self, name: str, params: dict[str, Any]) -> _RpcQuery:
        assert name == "append_financial_event"
        return _RpcQuery(self, params)


@pytest.mark.asyncio
async def test_owner_approval_stages_collections_without_second_policy_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph

    monkeypatch.setattr(graph, "make_async_llm_client", lambda **_: MagicMock())
    db = _StatefulDb()
    service = InboxService(db, TENANT_ID)  # type: ignore[arg-type]

    response = await asyncio.wait_for(
        service.approve(PARENT_TASK_ID, OWNER_ID),
        timeout=2,
    )

    assert response.materialised is True
    assert response.entity_type == "finance_ops_action_item"
    assert response.entity_id == "finance-ops-plan-1-ar"
    assert response.materialisation["dispatched_tool"] == "draft_collection_reminders"
    assert response.materialisation["child_review_tasks_created"] == 1
    assert db.tables["hitl_tasks"][0]["status"] == "done"
    assert db.tables["agent_suggestions"][0]["status"] == "approved"

    staged_suggestions = db.inserts["agent_suggestions"]
    assert len(staged_suggestions) == 1
    assert staged_suggestions[0]["agent_name"] == "collections_agent"
    assert staged_suggestions[0]["action_type"] == "send_email"
    assert staged_suggestions[0]["status"] == "pending"
    staged_tasks = db.inserts["hitl_tasks"]
    assert len(staged_tasks) == 1
    assert staged_tasks[0]["kind"] == "send_email"
    assert staged_tasks[0]["status"] == "open"

    assert [row["tool_name"] for row in db.inserts["agent_tool_invocations"]] == [
        "find_overdue_invoices",
        "draft_collection_email",
        "send_email",
    ]
    assert db.inserts["agent_tool_invocations"][-1]["status"] == "skipped"
    assert db.tables["financial_events"][0]["event_type"] == "hitl_task.approved"
    assert "agent_autonomy_settings" not in db.table_calls


@pytest.mark.asyncio
async def test_failed_collections_staging_keeps_parent_action_item_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph

    monkeypatch.setattr(graph, "make_async_llm_client", lambda **_: MagicMock())
    db = _StatefulDb(fail_invoice_read=True)
    service = InboxService(db, TENANT_ID)  # type: ignore[arg-type]

    with pytest.raises(HTTPException) as exc:
        await service.approve(PARENT_TASK_ID, OWNER_ID)

    assert exc.value.status_code == 409
    assert "Plan Item dispatch failed" in str(exc.value.detail)
    assert db.tables["hitl_tasks"][0]["status"] == "open"
    assert db.tables["agent_suggestions"][0]["status"] == "pending"
    assert db.inserts.get("agent_suggestions", []) == []
    assert db.inserts.get("hitl_tasks", []) == []
    assert db.tables["financial_events"] == []
    assert db.tables["agent_runs"][0]["status"] == "failed"
