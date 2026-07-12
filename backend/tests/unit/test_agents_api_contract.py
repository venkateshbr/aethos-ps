"""Agents API contract tests for RLS-backed reads and service-role writes."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.tenant import get_tenant_id
from app.main import app
from app.services.agent_run_ledger import stable_payload_hash

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-1"


class _Query:
    def __init__(self, db: _DbBase, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, Any]] = []
        self._in_filters: list[tuple[str, list[Any]]] = []
        self._is_filters: list[tuple[str, Any]] = []
        self._not_is_filters: list[tuple[str, Any]] = []
        self._gte_filters: list[tuple[str, Any]] = []
        self._lte_filters: list[tuple[str, Any]] = []
        self._order_key: str | None = None
        self._order_desc = False
        self._limit: int | None = None
        self._upsert_payload: dict[str, Any] | None = None
        self._negate_next = False

    def select(self, *_args: Any, **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def in_(self, key: str, values: list[Any]) -> _Query:
        self._in_filters.append((key, values))
        return self

    def is_(self, key: str, value: Any) -> _Query:
        if self._negate_next:
            self._not_is_filters.append((key, value))
            self._negate_next = False
        else:
            self._is_filters.append((key, value))
        return self

    @property
    def not_(self) -> _Query:
        self._negate_next = True
        return self

    def gte(self, key: str, value: Any) -> _Query:
        self._gte_filters.append((key, value))
        return self

    def lte(self, key: str, value: Any) -> _Query:
        self._lte_filters.append((key, value))
        return self

    def order(self, key: str, desc: bool = False) -> _Query:
        self._order_key = key
        self._order_desc = desc
        return self

    def limit(self, limit: int) -> _Query:
        self._limit = limit
        return self

    def upsert(self, payload: dict[str, Any], **_kwargs: Any) -> _Query:
        self._upsert_payload = dict(payload)
        return self

    def execute(self) -> SimpleNamespace:
        if self._upsert_payload is not None:
            row = self._upsert_row()
            return SimpleNamespace(data=[deepcopy(row)])

        rows = [row for row in self.db.tables[self.table] if self._matches(row)]
        if self._order_key is not None:
            rows.sort(
                key=lambda row: str(row.get(self._order_key) or ""),
                reverse=self._order_desc,
            )
        if self._limit is not None:
            rows = rows[: self._limit]
        return SimpleNamespace(data=deepcopy(rows))

    def _upsert_row(self) -> dict[str, Any]:
        assert self._upsert_payload is not None
        if self.table == "finance_ops_schedules":
            rows = self.db.tables[self.table]
            tenant_id = self._upsert_payload["tenant_id"]
            for row in rows:
                if row["tenant_id"] == tenant_id:
                    row.update(self._upsert_payload)
                    return row
            row = dict(self._upsert_payload)
            rows.append(row)
            return row

        key = (
            self._upsert_payload["tenant_id"],
            self._upsert_payload["agent_name"],
            self._upsert_payload["action_type"],
        )
        rows = self.db.tables[self.table]
        for row in rows:
            if (row["tenant_id"], row["agent_name"], row["action_type"]) == key:
                row.update(self._upsert_payload)
                return row

        row = {
            "level": 2,
            "is_enabled": True,
            "failure_count": 0,
            "failure_threshold": 3,
            "circuit_open_until": None,
            "circuit_open_reason": None,
            "l3_opt_in": False,
            "eval_passed_at": None,
            "eval_score": None,
            "max_auto_risk": "draft",
            **self._upsert_payload,
        }
        rows.append(row)
        return row

    def _matches(self, row: dict[str, Any]) -> bool:
        for key, value in self._eq_filters:
            if row.get(key) != value:
                return False
        for key, values in self._in_filters:
            if row.get(key) not in values:
                return False
        for key, value in self._is_filters:
            if value == "null":
                if row.get(key) is not None:
                    return False
            elif row.get(key) is not value:
                return False
        for key, value in self._not_is_filters:
            if value == "null":
                if row.get(key) is None:
                    return False
            elif row.get(key) is value:
                return False
        for key, value in self._gte_filters:
            if row.get(key) < value:
                return False
        for key, value in self._lte_filters:
            if row.get(key) > value:
                return False
        return True


class _DbBase:
    def __init__(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        self.tables = tables

    def table(self, name: str) -> _Query:
        assert name in self.tables
        return _Query(self, name)

    def rpc(self, _name: str, _params: dict[str, Any]) -> SimpleNamespace:
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=[]))


def _run_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "id": "run-1",
        "tenant_id": TENANT_ID,
        "agent_name": "copilot_agent",
        "trigger_type": "chat",
        "status": "succeeded",
        "user_id": "user-1",
        "source_document_hash": None,
        "prompt_version": "cop-v1",
        "model_version": "model-a",
        "input_hash": "input-hash",
        "output_hash": "output-hash",
        "usage_input_tokens": 10,
        "usage_output_tokens": 20,
        "cost_usd": "0.001000",
        "trace_id": "trace-1",
        "replay_pointer": "chat_threads/thread-1",
        "error_message": None,
        "started_at": "2026-06-22T06:00:00Z",
        "completed_at": "2026-06-22T06:00:01Z",
        "created_at": "2026-06-22T06:00:00Z",
    }
    row.update(overrides)
    return row


def _tool_row(**overrides: Any) -> dict[str, Any]:
    input_snapshot = overrides.get("input_snapshot", {"status": "active", "limit": 10})
    output_snapshot = overrides.get(
        "output_snapshot",
        {
            "count": 1,
            "engagements": [
                {
                    "id": "eng-1",
                    "name": "Meridian Advisory",
                    "billing_arrangement": "time_and_materials",
                    "currency": "USD",
                    "total_value": "12000.00",
                    "status": "active",
                }
            ],
        },
    )
    row = {
        "id": "tool-1",
        "tenant_id": TENANT_ID,
        "agent_run_id": "run-1",
        "tool_name": "query_engagements",
        "risk_class": "read_only",
        "status": "succeeded",
        "external_tool_call_id": "call-1",
        "input_hash": stable_payload_hash(input_snapshot),
        "output_hash": stable_payload_hash(output_snapshot),
        "input_snapshot": input_snapshot,
        "output_snapshot": output_snapshot,
        "duration_ms": 12,
        "error_message": None,
        "created_at": "2026-06-22T06:00:00Z",
    }
    row.update(overrides)
    return row


def _workflow_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "id": "workflow-1",
        "tenant_id": TENANT_ID,
        "workflow_name": "monthly_retainer_billing_run",
        "status": "waiting_on_human",
        "owner_agent_name": "billing_run_agent",
        "user_id": None,
        "current_step": "awaiting_billing_run_review",
        "goal_snapshot": {"period_start": "2026-06-01"},
        "state_snapshot": {"billing_run_id": "billing-run-1"},
        "trace_id": "trace-workflow-1",
        "replay_pointer": "billing_runs/billing-run-1",
        "error_message": None,
        "started_at": "2026-06-22T06:00:00Z",
        "completed_at": None,
        "created_at": "2026-06-22T06:00:00Z",
        "updated_at": "2026-06-22T06:00:01Z",
    }
    row.update(overrides)
    return row


class _ReadDb(_DbBase):
    def __init__(self) -> None:
        super().__init__(
            {
                "agent_suggestions": [
                    {
                        "id": "suggestion-1",
                        "tenant_id": TENANT_ID,
                        "agent_name": "copilot_agent",
                        "action_type": "default",
                        "status": "approved",
                        "confidence": "0.98",
                        "created_at": "2026-06-22T06:00:00Z",
                    }
                ],
                "agent_autonomy_settings": [
                    {
                        "tenant_id": TENANT_ID,
                        "agent_name": "copilot_agent",
                        "action_type": "default",
                        "level": 2,
                        "is_enabled": True,
                        "failure_count": 0,
                        "failure_threshold": 3,
                        "circuit_open_until": None,
                        "circuit_open_reason": None,
                        "l3_opt_in": False,
                        "eval_passed_at": None,
                        "eval_score": None,
                        "max_auto_risk": "draft",
                    }
                ],
                "finance_ops_schedules": [],
                "agent_runs": [_run_row()],
                "agent_workflow_runs": [_workflow_row()],
                "agent_tool_invocations": [
                    _tool_row(id="tool-2", status="failed", created_at="2026-06-22T06:00:01Z"),
                    _tool_row(id="tool-1", status="succeeded", created_at="2026-06-22T06:00:00Z"),
                ],
                "engagements": [
                    {
                        "id": "eng-1",
                        "tenant_id": TENANT_ID,
                        "name": "Meridian Advisory",
                        "billing_arrangement": "time_and_materials",
                        "currency": "USD",
                        "total_value": "12000.00",
                        "status": "active",
                        "deleted_at": None,
                    }
                ],
                "agent_eval_candidates": [
                    {
                        "id": "candidate-1",
                        "tenant_id": TENANT_ID,
                        "agent_correction_id": "correction-1",
                        "agent_suggestion_id": "suggestion-1",
                        "agent_name": "copilot_agent",
                        "action_type": "copilot_update_rate_card",
                        "eval_case_key": "copilot_agent:copilot_update_rate_card:correction:correction-1",
                        "status": "candidate",
                        "input_hash": "input-hash",
                        "original_output_hash": "original-hash",
                        "corrected_output_hash": "corrected-hash",
                        "reason": "human_edit",
                        "created_at": "2026-06-22T06:00:00Z",
                        "updated_at": "2026-06-22T06:00:00Z",
                    }
                ],
            }
        )


class _WriteDb(_DbBase):
    def __init__(self) -> None:
        super().__init__({"agent_autonomy_settings": [], "finance_ops_schedules": []})


class _ControlRoomDb(_DbBase):
    def __init__(self) -> None:
        super().__init__(
            {
                "tenants": [{"id": TENANT_ID, "status": "active"}],
                "tenant_users": [{"id": "tu-1", "tenant_id": TENANT_ID}],
                "finance_ops_schedules": [
                    {
                        "tenant_id": TENANT_ID,
                        "is_enabled": True,
                        "cadence": "weekly",
                        "run_hour_utc": 8,
                        "run_weekday_utc": 0,
                        "timezone": "UTC",
                        "period_mode": "current_month",
                        "lookback_limit": 10,
                        "stale_after_hours": 24,
                        "high_risk_stale_after_hours": 4,
                        "escalation_enabled": True,
                        "created_at": "2026-06-22T00:00:00Z",
                        "updated_at": "2026-06-22T00:00:00Z",
                    }
                ],
                "agent_runs": [],
                "agent_tool_invocations": [],
                "agent_workflow_runs": [
                    _workflow_row(
                        id="workflow-scheduled-2",
                        workflow_name="scheduled_finance_ops_manager",
                        status="waiting_on_human",
                        owner_agent_name="finance_ops_manager",
                        current_step="hitl_review",
                        goal_snapshot={"cadence": "weekly"},
                        state_snapshot={
                            "period": "2026-06",
                            "plan_created": True,
                            "escalations_created": 1,
                        },
                        created_at="2026-06-22T08:00:00Z",
                        started_at="2026-06-22T08:00:00Z",
                        updated_at="2026-06-22T08:00:02Z",
                    ),
                    _workflow_row(
                        id="workflow-scheduled-1",
                        workflow_name="scheduled_finance_ops_manager",
                        status="failed",
                        owner_agent_name="finance_ops_manager",
                        current_step="failed",
                        state_snapshot={"result": "failed"},
                        error_message="traceback should not leak",
                        created_at="2026-06-21T08:00:00Z",
                        started_at="2026-06-21T08:00:00Z",
                        updated_at="2026-06-21T08:00:02Z",
                    ),
                    _workflow_row(
                        id="workflow-close-1",
                        workflow_name="monthly_close_preparation",
                        status="skipped",
                        owner_agent_name="close_controller",
                        current_step="completed",
                        created_at="2026-06-21T07:00:00Z",
                        started_at="2026-06-21T07:00:00Z",
                        updated_at="2026-06-21T07:00:01Z",
                    ),
                ],
                "hitl_tasks": [
                    {
                        "id": "task-plan",
                        "tenant_id": TENANT_ID,
                        "kind": "copilot_create_finance_ops_action_plan",
                        "priority": "high",
                        "title": "Review scheduled Finance Ops action plan",
                        "payload": {
                            "period": "2026-06",
                            "action_count": 3,
                            "source_schedule_key": "tenant-1:weekly:2026-06-22",
                        },
                        "status": "open",
                        "created_at": "2026-06-22T08:00:03Z",
                        "updated_at": "2026-06-22T08:00:03Z",
                    },
                    {
                        "id": "task-item",
                        "tenant_id": TENANT_ID,
                        "kind": "finance_ops_action_item",
                        "priority": "normal",
                        "title": "Draft invoice for WIP",
                        "payload": {"period": "2026-06", "risk_class": "draft"},
                        "status": "open",
                        "created_at": "2026-06-22T08:00:04Z",
                        "updated_at": "2026-06-22T08:00:04Z",
                    },
                    {
                        "id": "task-escalation",
                        "tenant_id": TENANT_ID,
                        "kind": "finance_ops_escalation",
                        "priority": "critical",
                        "title": "Escalate stale AI review",
                        "payload": {
                            "risk_class": "write_money_out",
                            "required_approval_role": "admin",
                        },
                        "status": "in_progress",
                        "created_at": "2026-06-22T08:00:05Z",
                        "updated_at": "2026-06-22T08:00:05Z",
                    },
                    {
                        "id": "task-done",
                        "tenant_id": TENANT_ID,
                        "kind": "finance_ops_action_item",
                        "priority": "normal",
                        "title": "Completed item",
                        "payload": {},
                        "status": "done",
                        "created_at": "2026-06-22T08:00:06Z",
                        "updated_at": "2026-06-22T08:00:06Z",
                    },
                ],
                "accounting_close_tasks": [],
                "accounting_close_overrides": [],
                "financial_events": [],
            }
        )


class _ApprovalControlsDb(_DbBase):
    def __init__(self) -> None:
        super().__init__(
            {
                "tenant_users": [
                    {
                        "id": "tu-manager",
                        "tenant_id": TENANT_ID,
                        "user_id": "manager-1",
                        "role": "manager",
                        "deleted_at": None,
                    },
                    {
                        "id": "tu-viewer",
                        "tenant_id": TENANT_ID,
                        "user_id": "viewer-1",
                        "role": "viewer",
                        "deleted_at": None,
                    },
                ],
                "tenant_approval_policies": [
                    {
                        "tenant_id": TENANT_ID,
                        "money_out_default_role": "admin",
                        "money_out_owner_threshold": "25000",
                        "money_out_owner_role": "owner",
                        "accounting_role": "admin",
                        "manual_journal_approval_threshold": "10000",
                        "money_in_role": "manager",
                        "draft_role": "manager",
                        "external_send_role": "admin",
                        "high_risk_role": "admin",
                    }
                ],
                "hitl_tasks": [
                    {
                        "id": "task-owner-pay",
                        "tenant_id": TENANT_ID,
                        "kind": "create_bill_payment_batch",
                        "priority": "high",
                        "title": "Review high-value bill-pay batch",
                        "payload": {
                            "total_amount": "75000",
                            "vendor_name": "Forster & Reid",
                            "internal_secret": "should not leak",
                        },
                        "status": "open",
                        "created_at": "2026-06-22T10:00:00Z",
                        "updated_at": "2026-06-22T10:00:00Z",
                    },
                    {
                        "id": "task-journal",
                        "tenant_id": TENANT_ID,
                        "kind": "create_manual_journal",
                        "priority": "normal",
                        "title": "Review payroll accrual journal",
                        "payload": {
                            "total_debits": "15000",
                            "business_reason": "June accrual",
                        },
                        "status": "open",
                        "created_at": "2026-06-22T09:00:00Z",
                        "updated_at": "2026-06-22T09:00:00Z",
                    },
                    {
                        "id": "task-invoice",
                        "tenant_id": TENANT_ID,
                        "kind": "copilot_draft_invoice",
                        "priority": "normal",
                        "title": "Review customer invoice draft",
                        "payload": {"total_amount": "1200"},
                        "status": "open",
                        "created_at": "2026-06-22T08:00:00Z",
                        "updated_at": "2026-06-22T08:00:00Z",
                    },
                    {
                        "id": "task-foreign",
                        "tenant_id": "tenant-foreign",
                        "kind": "create_bill_payment_batch",
                        "priority": "critical",
                        "title": "Foreign tenant task",
                        "payload": {"total_amount": "999999"},
                        "status": "open",
                        "created_at": "2026-06-22T11:00:00Z",
                        "updated_at": "2026-06-22T11:00:00Z",
                    },
                ],
            }
        )


class _O2CReadDb(_DbBase):
    def __init__(self) -> None:
        super().__init__(
            {
                "clients": [
                    {
                        "id": "client-northstar",
                        "tenant_id": TENANT_ID,
                        "name": "Northstar Advisory",
                        "deleted_at": None,
                    },
                    {
                        "id": "client-brightwater",
                        "tenant_id": TENANT_ID,
                        "name": "Brightwater Payroll",
                        "deleted_at": None,
                    },
                    {
                        "id": "client-foreign",
                        "tenant_id": "tenant-foreign",
                        "name": "Foreign Client",
                        "deleted_at": None,
                    },
                ],
                "invoices": [
                    {
                        "id": "inv-overdue",
                        "tenant_id": TENANT_ID,
                        "engagement_id": "eng-1",
                        "client_id": "client-northstar",
                        "invoice_number": "INV-1001",
                        "currency": "USD",
                        "subtotal": "10000",
                        "tax_total": "0",
                        "total": "10000",
                        "status": "sent",
                        "issue_date": "2026-05-01",
                        "due_date": "2026-05-15",
                        "paid_at": None,
                        "stripe_payment_link_id": "plink-1",
                        "stripe_payment_link_url": "https://pay.example/inv-1001",
                        "public_token": "public-token",
                        "sent_at": "2026-05-01T12:00:00Z",
                        "notes": None,
                        "created_at": "2026-05-01T12:00:00Z",
                        "updated_at": "2026-05-01T12:00:00Z",
                        "deleted_at": None,
                        "clients": {"name": "Northstar Advisory"},
                    },
                    {
                        "id": "inv-current",
                        "tenant_id": TENANT_ID,
                        "engagement_id": "eng-1",
                        "client_id": "client-northstar",
                        "invoice_number": "INV-1002",
                        "currency": "USD",
                        "subtotal": "5000",
                        "tax_total": "0",
                        "total": "5000",
                        "status": "approved",
                        "issue_date": "2026-06-20",
                        "due_date": "2026-07-15",
                        "paid_at": None,
                        "stripe_payment_link_id": None,
                        "stripe_payment_link_url": None,
                        "public_token": "public-token-2",
                        "sent_at": None,
                        "notes": None,
                        "created_at": "2026-06-20T12:00:00Z",
                        "updated_at": "2026-06-20T12:00:00Z",
                        "deleted_at": None,
                        "clients": {"name": "Northstar Advisory"},
                    },
                    {
                        "id": "inv-disputed",
                        "tenant_id": TENANT_ID,
                        "engagement_id": "eng-1",
                        "client_id": "client-northstar",
                        "invoice_number": "INV-1003",
                        "currency": "USD",
                        "subtotal": "7000",
                        "tax_total": "0",
                        "total": "7000",
                        "status": "sent",
                        "issue_date": "2026-05-01",
                        "due_date": "2026-05-20",
                        "paid_at": None,
                        "stripe_payment_link_id": None,
                        "stripe_payment_link_url": None,
                        "public_token": "public-token-3",
                        "sent_at": "2026-05-01T12:00:00Z",
                        "notes": "Disputed by client; do not chase",
                        "created_at": "2026-05-01T12:00:00Z",
                        "updated_at": "2026-05-01T12:00:00Z",
                        "deleted_at": None,
                        "clients": {"name": "Northstar Advisory"},
                    },
                    {
                        "id": "inv-paid",
                        "tenant_id": TENANT_ID,
                        "engagement_id": "eng-2",
                        "client_id": "client-brightwater",
                        "invoice_number": "INV-2001",
                        "currency": "GBP",
                        "subtotal": "1200",
                        "tax_total": "0",
                        "total": "1200",
                        "status": "paid",
                        "issue_date": "2026-06-01",
                        "due_date": "2026-06-15",
                        "paid_at": "2026-06-18T10:00:00Z",
                        "stripe_payment_link_id": None,
                        "stripe_payment_link_url": None,
                        "public_token": "public-paid",
                        "sent_at": "2026-06-01T12:00:00Z",
                        "notes": None,
                        "created_at": "2026-06-01T12:00:00Z",
                        "updated_at": "2026-06-18T10:00:00Z",
                        "deleted_at": None,
                        "clients": {"name": "Brightwater Payroll"},
                    },
                    {
                        "id": "inv-foreign",
                        "tenant_id": "tenant-foreign",
                        "engagement_id": "eng-foreign",
                        "client_id": "client-foreign",
                        "invoice_number": "INV-9999",
                        "currency": "USD",
                        "subtotal": "99999",
                        "tax_total": "0",
                        "total": "99999",
                        "status": "sent",
                        "issue_date": "2026-05-01",
                        "due_date": "2026-05-02",
                        "paid_at": None,
                        "stripe_payment_link_id": None,
                        "stripe_payment_link_url": None,
                        "public_token": "foreign-token",
                        "sent_at": "2026-05-01T12:00:00Z",
                        "notes": "foreign tenant secret",
                        "created_at": "2026-05-01T12:00:00Z",
                        "updated_at": "2026-05-01T12:00:00Z",
                        "deleted_at": None,
                        "clients": {"name": "Foreign Client"},
                    },
                ],
                "payments": [
                    {
                        "id": "pay-1",
                        "tenant_id": TENANT_ID,
                        "invoice_id": "inv-overdue",
                        "amount": "2000",
                        "currency": "USD",
                        "base_amount": "2000",
                        "paid_at": "2026-06-01T10:00:00Z",
                        "notes": "partial wire",
                    },
                    {
                        "id": "pay-2",
                        "tenant_id": TENANT_ID,
                        "invoice_id": "inv-paid",
                        "amount": "1200",
                        "currency": "GBP",
                        "base_amount": "1500",
                        "paid_at": "2026-06-18T10:00:00Z",
                        "notes": None,
                    },
                ],
                "agent_suggestions": [
                    {
                        "id": "sug-1",
                        "tenant_id": TENANT_ID,
                        "agent_name": "collections_agent",
                        "action_type": "send_email",
                        "status": "approved",
                        "related_entity_id": "inv-overdue",
                        "output_snapshot": {
                            "invoice_id": "inv-overdue",
                            "tone": "firm",
                            "body_html": "should not leak",
                        },
                        "created_at": "2026-06-20T10:00:00Z",
                    }
                ],
                "collections_policies": [
                    {
                        "id": "policy-1",
                        "tenant_id": TENANT_ID,
                        "client_id": None,
                        "is_enabled": True,
                        "gentle_after_days": 1,
                        "firm_after_days": 8,
                        "final_after_days": 31,
                        "cooldown_days": 7,
                        "max_reminders_per_invoice": 3,
                        "max_auto_send_tone": "final",
                        "deleted_at": None,
                    }
                ],
            }
        )


class _P2PReadDb(_DbBase):
    def __init__(self) -> None:
        super().__init__(
            {
                "clients": [
                    {
                        "id": "vendor-forster",
                        "tenant_id": TENANT_ID,
                        "name": "Forster & Reid Ltd",
                        "kind": "vendor",
                        "deleted_at": None,
                    },
                    {
                        "id": "vendor-foreign",
                        "tenant_id": "tenant-foreign",
                        "name": "Foreign Vendor",
                        "kind": "vendor",
                        "deleted_at": None,
                    },
                ],
                "bills": [
                    {
                        "id": "bill-ready",
                        "tenant_id": TENANT_ID,
                        "client_id": "vendor-forster",
                        "purchase_order_id": "po-1",
                        "bill_number": "BILL-1001",
                        "currency": "USD",
                        "subtotal": "3000",
                        "tax_total": "0",
                        "total": "3000",
                        "status": "approved",
                        "issue_date": "2026-06-20",
                        "due_date": "2026-07-05",
                        "paid_at": None,
                        "vendor_invoice_number": "FR-1001",
                        "po_match_status": "matched",
                        "po_match_summary": {"status": "matched", "line_exceptions": []},
                        "vendor_invoice_review": {"possible_duplicate": False},
                        "source_document_id": "doc-ready",
                        "notes": None,
                        "created_at": "2026-06-20T09:00:00Z",
                        "updated_at": "2026-06-20T09:00:00Z",
                        "deleted_at": None,
                        "clients": {"name": "Forster & Reid Ltd"},
                    },
                    {
                        "id": "bill-duplicate",
                        "tenant_id": TENANT_ID,
                        "client_id": "vendor-forster",
                        "purchase_order_id": None,
                        "bill_number": "BILL-1002",
                        "currency": "USD",
                        "subtotal": "4000",
                        "tax_total": "0",
                        "total": "4000",
                        "status": "approved",
                        "issue_date": "2026-06-18",
                        "due_date": "2026-07-02",
                        "paid_at": None,
                        "vendor_invoice_number": "FR-DUP",
                        "po_match_status": "not_linked",
                        "po_match_summary": {},
                        "vendor_invoice_review": {
                            "possible_duplicate": True,
                            "duplicate_review": {},
                        },
                        "source_document_id": "doc-dup",
                        "notes": None,
                        "created_at": "2026-06-18T09:00:00Z",
                        "updated_at": "2026-06-18T09:00:00Z",
                        "deleted_at": None,
                        "clients": {"name": "Forster & Reid Ltd"},
                    },
                    {
                        "id": "bill-scheduled",
                        "tenant_id": TENANT_ID,
                        "client_id": "vendor-forster",
                        "purchase_order_id": "po-2",
                        "bill_number": "BILL-1003",
                        "currency": "USD",
                        "subtotal": "2500",
                        "tax_total": "0",
                        "total": "2500",
                        "status": "approved",
                        "issue_date": "2026-06-10",
                        "due_date": "2026-06-30",
                        "paid_at": None,
                        "vendor_invoice_number": "FR-1003",
                        "po_match_status": "matched",
                        "po_match_summary": {"status": "matched"},
                        "vendor_invoice_review": {"possible_duplicate": False},
                        "source_document_id": "doc-scheduled",
                        "notes": None,
                        "created_at": "2026-06-10T09:00:00Z",
                        "updated_at": "2026-06-10T09:00:00Z",
                        "deleted_at": None,
                        "clients": {"name": "Forster & Reid Ltd"},
                    },
                    {
                        "id": "bill-paid",
                        "tenant_id": TENANT_ID,
                        "client_id": "vendor-forster",
                        "purchase_order_id": None,
                        "bill_number": "BILL-1004",
                        "currency": "USD",
                        "subtotal": "900",
                        "tax_total": "0",
                        "total": "900",
                        "status": "paid",
                        "issue_date": "2026-05-01",
                        "due_date": "2026-05-31",
                        "paid_at": "2026-06-01T10:00:00Z",
                        "vendor_invoice_number": "FR-1004",
                        "po_match_status": "not_linked",
                        "po_match_summary": {},
                        "vendor_invoice_review": {},
                        "source_document_id": "doc-paid",
                        "notes": None,
                        "created_at": "2026-05-01T09:00:00Z",
                        "updated_at": "2026-06-01T10:00:00Z",
                        "deleted_at": None,
                        "clients": {"name": "Forster & Reid Ltd"},
                    },
                    {
                        "id": "bill-foreign",
                        "tenant_id": "tenant-foreign",
                        "client_id": "vendor-foreign",
                        "purchase_order_id": None,
                        "bill_number": "BILL-9999",
                        "currency": "USD",
                        "subtotal": "99999",
                        "tax_total": "0",
                        "total": "99999",
                        "status": "approved",
                        "issue_date": "2026-06-01",
                        "due_date": "2026-06-15",
                        "paid_at": None,
                        "vendor_invoice_number": "FV-9999",
                        "po_match_status": "not_linked",
                        "po_match_summary": {},
                        "vendor_invoice_review": {},
                        "source_document_id": "foreign-doc",
                        "notes": "foreign bank secret",
                        "created_at": "2026-06-01T09:00:00Z",
                        "updated_at": "2026-06-01T09:00:00Z",
                        "deleted_at": None,
                        "clients": {"name": "Foreign Vendor"},
                    },
                ],
                "bill_lines": [
                    {
                        "id": "line-ready",
                        "tenant_id": TENANT_ID,
                        "bill_id": "bill-ready",
                        "description": "Subcontractor services",
                        "quantity": "1",
                        "unit_price": "3000",
                        "amount": "3000",
                        "tax_amount": "0",
                        "account_id": "acct-expense",
                        "is_prepaid": False,
                        "service_start_date": None,
                        "service_end_date": None,
                        "created_at": "2026-06-20T09:00:00Z",
                    },
                    {
                        "id": "line-dup",
                        "tenant_id": TENANT_ID,
                        "bill_id": "bill-duplicate",
                        "description": "Consulting services",
                        "quantity": "1",
                        "unit_price": "4000",
                        "amount": "4000",
                        "tax_amount": "0",
                        "account_id": "acct-expense",
                        "is_prepaid": False,
                        "service_start_date": None,
                        "service_end_date": None,
                        "created_at": "2026-06-18T09:00:00Z",
                    },
                    {
                        "id": "line-scheduled",
                        "tenant_id": TENANT_ID,
                        "bill_id": "bill-scheduled",
                        "description": "Approved services",
                        "quantity": "1",
                        "unit_price": "2500",
                        "amount": "2500",
                        "tax_amount": "0",
                        "account_id": "acct-expense",
                        "is_prepaid": False,
                        "service_start_date": None,
                        "service_end_date": None,
                        "created_at": "2026-06-10T09:00:00Z",
                    },
                ],
                "bill_payment_items": [
                    {
                        "id": "bpi-1",
                        "tenant_id": TENANT_ID,
                        "batch_id": "batch-1",
                        "bill_id": "bill-scheduled",
                        "amount": "2500",
                        "currency": "USD",
                        "status": "pending",
                        "created_at": "2026-06-24T09:00:00Z",
                    }
                ],
                "bill_payment_batches": [
                    {
                        "id": "batch-1",
                        "tenant_id": TENANT_ID,
                        "status": "approved",
                        "total": "2500",
                        "currency": "USD",
                        "bank_account_label": "Operating account should not leak",
                        "pay_date": "2026-06-30",
                        "file_format": "csv",
                        "exported_at": "2026-06-24T10:00:00Z",
                        "export_file_sha256": "a" * 64,
                        "sent_at": None,
                        "settled_at": None,
                        "risk_review_required": True,
                    }
                ],
            }
        )


class _R2RReadDb(_DbBase):
    def __init__(self, *, locked: bool = True, include_tasks: bool = True) -> None:
        period_locks = [
            {
                "tenant_id": TENANT_ID,
                "period": "2026-06",
                "locked_at": "2026-07-05T10:00:00Z",
                "locked_by": "controller-1",
            }
        ] if locked else []
        close_tasks = [
            {
                "id": "task-reconcile",
                "tenant_id": TENANT_ID,
                "period": "2026-06",
                "code": "subledger_reconciliation",
                "title": "Reconcile AR/AP subledgers",
                "status": "done",
                "owner_role": "finance_manager",
                "due_date": "2026-07-05",
                "order_index": 10,
                "deleted_at": None,
            },
            {
                "id": "task-tb",
                "tenant_id": TENANT_ID,
                "period": "2026-06",
                "code": "trial_balance_review",
                "title": "Review trial balance",
                "status": "open",
                "owner_role": "controller",
                "due_date": "2026-07-05",
                "order_index": 40,
                "deleted_at": None,
            },
        ] if include_tasks else []
        super().__init__(
            {
                "tenants": [{"id": TENANT_ID, "base_currency": "USD"}],
                "period_locks": period_locks,
                "journal_entries": [
                    _journal_entry(
                        "je-may-rev",
                        period="2026-05",
                        reference_type="invoice",
                        reference_id="inv-may",
                    ),
                    _journal_entry(
                        "je-may-exp",
                        period="2026-05",
                        reference_type="bill",
                        reference_id="bill-may",
                    ),
                    _journal_entry(
                        "je-june-rev",
                        period="2026-06",
                        reference_type="invoice",
                        reference_id="inv-june",
                    ),
                    _journal_entry(
                        "je-june-exp",
                        period="2026-06",
                        reference_type="bill",
                        reference_id="bill-june",
                    ),
                    _journal_entry(
                        "je-draft",
                        period="2026-06",
                        reference_type="manual",
                        reference_id="accrual-1",
                        posted_at=None,
                        description="Draft payroll accrual",
                    ),
                    _journal_entry(
                        "je-foreign",
                        tenant_id="tenant-foreign",
                        period="2026-06",
                        reference_type="invoice",
                        reference_id="inv-foreign",
                        description="Foreign tenant journal",
                    ),
                ],
                "journal_lines": [
                    _journal_line("je-may-rev", "2026-05", "DR", "8000", "1200", "Accounts Receivable", "asset"),
                    _journal_line("je-may-rev", "2026-05", "CR", "8000", "4000", "Revenue", "revenue"),
                    _journal_line("je-may-exp", "2026-05", "DR", "5000", "5000", "Direct Costs", "expense"),
                    _journal_line("je-may-exp", "2026-05", "CR", "5000", "1100", "Bank", "asset"),
                    _journal_line("je-june-rev", "2026-06", "DR", "10000", "1200", "Accounts Receivable", "asset"),
                    _journal_line("je-june-rev", "2026-06", "CR", "10000", "4000", "Revenue", "revenue"),
                    _journal_line("je-june-exp", "2026-06", "DR", "6500", "5000", "Direct Costs", "expense"),
                    _journal_line("je-june-exp", "2026-06", "CR", "6500", "1100", "Bank", "asset"),
                    _journal_line(
                        "je-foreign",
                        "2026-06",
                        "CR",
                        "99999",
                        "4000",
                        "Foreign Revenue",
                        "revenue",
                        tenant_id="tenant-foreign",
                    ),
                ],
                "invoices": [
                    _r2r_invoice("inv-may", "INV-MAY", "2026-05-15", "8000"),
                    _r2r_invoice("inv-june", "INV-JUNE", "2026-06-15", "10000"),
                    _r2r_invoice(
                        "inv-foreign",
                        "INV-FOREIGN",
                        "2026-06-10",
                        "99999",
                        tenant_id="tenant-foreign",
                    ),
                ],
                "bills": [
                    _r2r_bill("bill-may", "BILL-MAY", "2026-05-20", "5000"),
                    _r2r_bill("bill-june", "BILL-JUNE", "2026-06-20", "6500"),
                ],
                "bank_transactions": [],
                "bank_reconciliation_matches": [],
                "agent_suggestions": [
                    {
                        "id": "review-close-1",
                        "tenant_id": TENANT_ID,
                        "agent_name": "close_agent",
                        "action_type": "draft_journal",
                        "status": "pending",
                        "output_snapshot": {
                            "period": "2026-06",
                            "currency": "USD",
                            "proposal_type": "recurring_journal",
                            "template_name": "Payroll accrual",
                            "journal_entry": {"reference": "close:2026-06:payroll"},
                        },
                    }
                ],
                "accounting_close_tasks": close_tasks,
                "accounting_close_overrides": [],
                "projects": [
                    {
                        "id": "project-low-margin",
                        "tenant_id": TENANT_ID,
                        "name": "Nexus Implementation",
                        "engagement_id": "eng-1",
                        "currency": "USD",
                        "budget": "12000",
                        "engagements": {
                            "rate_card_id": "rate-card-1",
                            "service_line": "advisory",
                        },
                    }
                ],
                "engagements": [
                    {
                        "id": "eng-1",
                        "tenant_id": TENANT_ID,
                        "name": "Nexus Advisory",
                        "service_line": "advisory",
                        "rate_card_id": "rate-card-1",
                    }
                ],
                "project_expenses": [
                    {
                        "id": "expense-1",
                        "tenant_id": TENANT_ID,
                        "project_id": "project-low-margin",
                        "expense_date": "2026-06-22",
                        "amount": "8500",
                        "base_amount": "8500",
                        "deleted_at": None,
                    }
                ],
                "time_entries": [
                    {
                        "id": "time-low-billable",
                        "tenant_id": TENANT_ID,
                        "employee_id": "employee-low",
                        "project_id": "project-low-margin",
                        "date": "2026-06-12",
                        "hours": "16",
                        "billable": True,
                        "billing_status": "unbilled",
                        "deleted_at": None,
                    },
                    {
                        "id": "time-low-admin",
                        "tenant_id": TENANT_ID,
                        "employee_id": "employee-low",
                        "project_id": "project-low-margin",
                        "date": "2026-06-13",
                        "hours": "24",
                        "billable": False,
                        "billing_status": "non_billable",
                        "deleted_at": None,
                    },
                ],
                "rate_card_lines": [
                    {
                        "id": "rate-1",
                        "tenant_id": TENANT_ID,
                        "rate_card_id": "rate-card-1",
                        "rate": "250",
                    }
                ],
                "invoice_lines": [
                    {
                        "id": "line-june",
                        "tenant_id": TENANT_ID,
                        "invoice_id": "inv-june",
                        "amount": "10000",
                        "service_catalogue_id": "svc-advisory",
                        "invoices": {
                            "status": "approved",
                            "issue_date": "2026-06-15",
                            "engagement_id": "eng-1",
                            "deleted_at": None,
                        },
                    }
                ],
                "service_catalogue": [
                    {
                        "id": "svc-advisory",
                        "tenant_id": TENANT_ID,
                        "service_line": "advisory",
                    }
                ],
                "employees": [
                    {
                        "id": "employee-low",
                        "tenant_id": TENANT_ID,
                        "cost_rate": "100",
                    }
                ],
            }
        )


class _R2RNoDataDb(_DbBase):
    def __init__(self) -> None:
        super().__init__(
            {
                "tenants": [{"id": TENANT_ID, "base_currency": "USD"}],
                "period_locks": [],
                "journal_entries": [
                    _journal_entry(
                        "je-foreign",
                        tenant_id="tenant-foreign",
                        period="2026-06",
                        reference_type="invoice",
                        reference_id="inv-foreign",
                        description="Foreign tenant secret journal",
                    )
                ],
                "journal_lines": [
                    _journal_line(
                        "je-foreign",
                        "2026-06",
                        "CR",
                        "99999",
                        "4000",
                        "Foreign Revenue",
                        "revenue",
                        tenant_id="tenant-foreign",
                    )
                ],
                "invoices": [],
                "bills": [],
                "bank_transactions": [],
                "bank_reconciliation_matches": [],
                "agent_suggestions": [],
                "accounting_close_tasks": [],
                "accounting_close_overrides": [],
                "projects": [],
                "engagements": [],
                "project_expenses": [],
                "time_entries": [],
                "rate_card_lines": [],
                "invoice_lines": [],
                "service_catalogue": [],
                "employees": [],
            }
        )


def _journal_entry(
    entry_id: str,
    *,
    tenant_id: str = TENANT_ID,
    period: str,
    reference_type: str,
    reference_id: str,
    posted_at: str | None = "2026-06-25T12:00:00Z",
    description: str = "Posted journal",
) -> dict[str, Any]:
    return {
        "id": entry_id,
        "tenant_id": tenant_id,
        "entry_number": entry_id.upper(),
        "description": description,
        "entry_date": f"{period}-25",
        "period": period,
        "reference_type": reference_type,
        "reference_id": reference_id,
        "posted_at": posted_at,
        "created_at": f"{period}-25T12:00:00Z",
    }


def _journal_line(
    journal_entry_id: str,
    period: str,
    direction: str,
    base_amount: str,
    account_code: str,
    account_name: str,
    account_type: str,
    *,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    return {
        "tenant_id": tenant_id,
        "journal_entry_id": journal_entry_id,
        "direction": direction,
        "base_amount": base_amount,
        "journal_entries": {
            "period": period,
            "posted_at": f"{period}-25T12:00:00Z",
            "description": f"{account_name} journal",
            "reference_type": "manual",
        },
        "accounts": {
            "code": account_code,
            "name": account_name,
            "account_type": account_type,
        },
    }


def _r2r_invoice(
    invoice_id: str,
    invoice_number: str,
    issue_date: str,
    total: str,
    *,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    return {
        "id": invoice_id,
        "tenant_id": tenant_id,
        "invoice_number": invoice_number,
        "engagement_id": "eng-1",
        "client_id": "client-1",
        "status": "approved",
        "issue_date": issue_date,
        "due_date": "2026-07-15",
        "total": total,
        "currency": "USD",
        "deleted_at": None,
    }


def _r2r_bill(
    bill_id: str,
    bill_number: str,
    issue_date: str,
    total: str,
) -> dict[str, Any]:
    return {
        "id": bill_id,
        "tenant_id": TENANT_ID,
        "bill_number": bill_number,
        "status": "approved",
        "issue_date": issue_date,
        "due_date": "2026-07-10",
        "total": total,
        "currency": "USD",
        "deleted_at": None,
    }


class _ForbiddenDb:
    def table(self, name: str) -> None:
        raise AssertionError(f"wrong dependency attempted to access {name}")

    def rpc(self, name: str, _params: dict[str, Any]) -> None:
        raise AssertionError(f"wrong dependency attempted to call {name}")


def _install_common_overrides() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="manager@example.com",
        role="manager",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID


def test_agent_dashboard_read_routes_use_rls_client() -> None:
    _install_common_overrides()
    app.dependency_overrides[get_user_rls_client] = lambda: _ReadDb()
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    try:
        with TestClient(app) as client:
            autonomy_response = client.get("/api/v1/agents/autonomy-status")
            runs_response = client.get(
                "/api/v1/agents/runs?agent_name=copilot_agent&status=succeeded&limit=10"
            )
            detail_response = client.get("/api/v1/agents/runs/run-1")
            workflow_runs_response = client.get(
                "/api/v1/agents/workflow-runs?status=waiting_on_human&limit=10"
            )
            workflow_detail_response = client.get(
                "/api/v1/agents/workflow-runs/workflow-1"
            )
            replay_response = client.post("/api/v1/agents/runs/run-1/replay")
            validation_response = client.post(
                "/api/v1/agents/runs/run-1/replay/validate"
            )
            candidates_response = client.get(
                "/api/v1/agents/eval-candidates?agent_name=copilot_agent&status=candidate"
            )
            finance_ops_schedule_response = client.get("/api/v1/agents/finance-ops/schedule")
    finally:
        app.dependency_overrides.clear()

    assert autonomy_response.status_code == 200, autonomy_response.text
    copilot = next(
        agent
        for agent in autonomy_response.json()["agents"]
        if agent["agent_name"] == "copilot_agent"
    )
    assert copilot["current_level"] == 2

    assert runs_response.status_code == 200, runs_response.text
    assert runs_response.json()["runs"][0]["id"] == "run-1"
    assert runs_response.json()["runs"][0]["tool_count"] == 2
    assert runs_response.json()["runs"][0]["failed_tool_count"] == 1

    assert detail_response.status_code == 200, detail_response.text
    assert [tool["id"] for tool in detail_response.json()["tool_invocations"]] == [
        "tool-1",
        "tool-2",
    ]

    assert workflow_runs_response.status_code == 200, workflow_runs_response.text
    workflow_body = workflow_runs_response.json()
    assert workflow_body["total"] == 1
    assert workflow_body["workflow_runs"][0]["id"] == "workflow-1"
    assert workflow_body["workflow_runs"][0]["status"] == "waiting_on_human"

    assert workflow_detail_response.status_code == 200, workflow_detail_response.text
    workflow_detail = workflow_detail_response.json()
    assert workflow_detail["workflow_name"] == "monthly_retainer_billing_run"
    assert workflow_detail["state_snapshot"]["billing_run_id"] == "billing-run-1"

    assert replay_response.status_code == 200, replay_response.text
    replay_body = replay_response.json()
    assert replay_body["run_id"] == "run-1"
    assert replay_body["replay_mode"] == "recorded_snapshot"
    assert replay_body["can_reexecute"] is False
    assert replay_body["manifest_hash"]
    assert [step["tool_invocation_id"] for step in replay_body["steps"]] == [
        "tool-1",
        "tool-2",
    ]

    assert validation_response.status_code == 200, validation_response.text
    validation_body = validation_response.json()
    assert validation_body["run_id"] == "run-1"
    assert validation_body["validation_mode"] == "current_code_dry_run"
    assert validation_body["overall_status"] == "matched"
    assert validation_body["reexecuted_step_count"] == 2
    assert validation_body["blocked_step_count"] == 0
    assert validation_body["steps"][0]["replay_status"] == "matched"

    assert candidates_response.status_code == 200, candidates_response.text
    assert candidates_response.json()["candidates"][0]["id"] == "candidate-1"

    assert finance_ops_schedule_response.status_code == 200, (
        finance_ops_schedule_response.text
    )
    finance_ops_schedule = finance_ops_schedule_response.json()
    assert finance_ops_schedule["tenant_id"] == TENANT_ID
    assert finance_ops_schedule["cadence"] == "daily"
    assert finance_ops_schedule["is_seeded_default"] is True


def test_agent_control_write_uses_service_role_client() -> None:
    write_db = _WriteDb()
    _install_common_overrides()
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: write_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/agents/copilot_agent/control",
                json={"is_enabled": False},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()["is_enabled"] is False
    assert write_db.tables["agent_autonomy_settings"][0]["agent_name"] == "copilot_agent"


def test_finance_ops_schedule_write_uses_service_role_client() -> None:
    write_db = _WriteDb()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="admin-1",
        email="admin@example.com",
        role="admin",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: write_db

    try:
        with TestClient(app) as client:
            response = client.put(
                "/api/v1/agents/finance-ops/schedule",
                json={
                    "is_enabled": True,
                    "cadence": "weekly",
                    "run_hour_utc": 8,
                    "run_weekday_utc": 2,
                    "timezone": "UTC",
                    "period_mode": "previous_month",
                    "lookback_limit": 12,
                    "stale_after_hours": 48,
                    "high_risk_stale_after_hours": 6,
                    "escalation_enabled": True,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["cadence"] == "weekly"
    assert body["run_weekday_utc"] == 2
    assert body["period_mode"] == "previous_month"
    assert body["is_seeded_default"] is False
    assert write_db.tables["finance_ops_schedules"][0]["tenant_id"] == TENANT_ID


def test_finance_ops_control_room_returns_sanitized_manager_view() -> None:
    db = _ControlRoomDb()
    _install_common_overrides()
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: db

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/agents/finance-ops/control-room?workflow_limit=10&task_limit=10"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tenant_id"] == TENANT_ID
    assert body["schedule"]["cadence"] == "weekly"
    assert body["next_run_at"] is not None
    assert body["latest_scheduled_run"]["id"] == "workflow-scheduled-2"
    assert body["latest_scheduled_run"]["period"] == "2026-06"
    assert body["recent_workflow_status_counts"]["waiting_on_human"] == 1
    assert body["recent_workflow_status_counts"]["failed"] == 1
    assert body["failed_or_skipped_workflows"][0]["has_error"] is True
    assert "traceback should not leak" not in str(body)
    assert body["open_action_plans"][0]["id"] == "task-plan"
    assert body["open_action_plans"][0]["action_count"] == 3
    assert body["open_plan_items"][0]["id"] == "task-item"
    assert body["open_escalations"][0]["required_approval_role"] == "admin"
    assert body["operational_health"]["status"] in {"ok", "degraded"}


def test_approval_controls_read_pack_returns_role_aware_manager_view() -> None:
    db = _ApprovalControlsDb()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="manager-1",
        email="manager@example.com",
        role="manager",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: db

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/agents/approval-controls/read-pack?inbox_limit=10")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tenant_id"] == TENANT_ID
    assert body["current_user_role"] == "manager"
    assert body["policy_source"] == "tenant_default"
    assert body["matched_persona_ids"] == [
        "finance_approver",
        "procurement_manager",
        "ap_lead",
        "ar_lead",
    ]

    rules = {rule["id"]: rule for rule in body["policy_rules"]}
    assert rules["money_in"]["current_user_can_approve"] is True
    assert rules["money_out_default"]["current_user_can_approve"] is False
    assert rules["money_out_owner_threshold"]["required_role"] == "owner"
    assert rules["money_out_owner_threshold"]["threshold"] == "25000"

    high_risk_ids = {item["id"] for item in body["pending_high_risk_inbox"]}
    assert {"task-owner-pay", "task-journal"} <= high_risk_ids
    higher_role_ids = {item["id"] for item in body["pending_items_requiring_higher_role"]}
    assert {"task-owner-pay", "task-journal"} <= higher_role_ids
    assert "task-invoice" not in higher_role_ids
    assert "task-foreign" not in str(body)
    assert "should not leak" not in str(body)


def test_approval_controls_read_pack_viewer_is_read_only() -> None:
    db = _ApprovalControlsDb()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="viewer-1",
        email="viewer@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: db

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/agents/approval-controls/read-pack?inbox_limit=10")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["current_user_role"] == "viewer"
    assert body["matched_persona_ids"] == ["executive"]
    assert all(rule["current_user_can_approve"] is False for rule in body["policy_rules"])
    assert {item["id"] for item in body["pending_items_requiring_higher_role"]} == {
        "task-owner-pay",
        "task-journal",
        "task-invoice",
    }
    assert any("cannot approve" in reason for reason in body["denied_action_explanations"])


def test_o2c_collections_read_pack_returns_customer_invoice_drilldown() -> None:
    db = _O2CReadDb()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="viewer-1",
        email="viewer@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: db

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/agents/o2c/collections/read-pack"
                "?client_name=Northstar&limit=10"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tenant_id"] == TENANT_ID
    assert body["totals"]["invoice_count"] == 3
    assert body["customers"][0]["client_name"] == "Northstar Advisory"

    invoices = {invoice["id"]: invoice for invoice in body["invoices"]}
    overdue = invoices["inv-overdue"]
    assert overdue["invoice_state"] == "partially_paid"
    assert overdue["payment_status"] == "partially_paid"
    assert overdue["paid_amount"] == "2000"
    assert overdue["balance_due"] == "8000"
    assert overdue["collections_policy_stage"] == "final"
    assert overdue["payment_link_state"] == "stripe_payment_link_available"
    assert overdue["reminder_history"]["count"] == 1
    assert overdue["reminder_history"]["last_tone"] == "firm"
    assert "final collections reminder" in overdue["recommended_next_action"]

    current = invoices["inv-current"]
    assert current["invoice_state"] == "current"
    assert current["aging_bucket"] == "current"

    disputed = invoices["inv-disputed"]
    assert disputed["invoice_state"] == "disputed"
    assert "invoice_disputed_or_on_hold" in disputed["reminder_blockers"]
    assert "Do not send" in disputed["recommended_next_action"]
    assert "should not leak" not in str(body)
    assert "foreign tenant secret" not in str(body)


def test_o2c_collections_read_pack_does_not_leak_cross_tenant_invoice_id() -> None:
    db = _O2CReadDb()
    _install_common_overrides()
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: db

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/agents/o2c/collections/read-pack?invoice_id=inv-foreign"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["totals"]["invoice_count"] == 0
    assert body["customers"] == []
    assert body["invoices"] == []


def test_p2p_payment_risk_read_pack_returns_vendor_bill_drilldown() -> None:
    db = _P2PReadDb()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="viewer-1",
        email="viewer@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: db

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/agents/p2p/payment-risk/read-pack"
                "?vendor_name=Forster&due_within_days=10&limit=10"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tenant_id"] == TENANT_ID
    assert body["totals"]["bill_count"] == 4
    assert body["vendors"][0]["vendor_name"] == "Forster & Reid Ltd"

    bills = {bill["id"]: bill for bill in body["bills"]}
    ready = bills["bill-ready"]
    assert ready["payment_readiness"] == "ready_for_payment_packet"
    assert ready["payment_blockers"] == []
    assert ready["coding_summary"]["status"] == "fully_coded"
    assert ready["source_document_available"] is True
    assert "Prepare a payment approval packet" in ready["recommended_next_action"]

    duplicate = bills["bill-duplicate"]
    assert duplicate["bill_state"] == "duplicate_risk"
    assert duplicate["duplicate_review_required"] is True
    assert "duplicate_review_required" in duplicate["payment_blockers"]

    scheduled = bills["bill-scheduled"]
    assert scheduled["payment_readiness"] == "scheduled"
    assert scheduled["payment_batches"][0]["batch_status"] == "approved"
    assert scheduled["payment_batches"][0]["export_file_hash_present"] is True
    assert "mark sent" in scheduled["recommended_next_action"].lower()

    paid = bills["bill-paid"]
    assert paid["payment_readiness"] == "paid"
    assert paid["recommended_next_action"] == "No payment action; the bill is paid."

    assert "Operating account should not leak" not in str(body)
    assert "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" not in str(body)
    assert "foreign bank secret" not in str(body)


def test_p2p_payment_risk_read_pack_does_not_leak_cross_tenant_bill_id() -> None:
    db = _P2PReadDb()
    _install_common_overrides()
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: db

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/agents/p2p/payment-risk/read-pack?bill_id=bill-foreign"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["totals"]["bill_count"] == 0
    assert body["vendors"] == []
    assert body["bills"] == []


def test_r2r_management_pack_read_pack_returns_close_reporting_drilldown() -> None:
    db = _R2RReadDb()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="viewer-1",
        email="viewer@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: db

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/agents/r2r/management-pack/read-pack"
                "?period=June%202026&comparison_period=2026-05-31&limit=5"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tenant_id"] == TENANT_ID
    assert body["period"] == "2026-06"
    assert body["comparison_period"] == "2026-05"
    assert body["financial_statements"]["current"]["trial_balance"]["is_balanced"] is True
    assert body["financial_statements"]["current"]["income_statement"]["total_revenue"] == "10000.00"
    assert body["statement_variances"][0]["code"] == "revenue"
    assert body["statement_variances"][0]["delta"] == "2000.00"
    assert body["close_status"]["locked"] is True
    assert body["close_task_checklist_state"]["status"] == "incomplete"
    assert body["journal_summary"]["draft_count"] == 1
    assert body["journal_summary"]["draft_journals"][0]["entry_number"] == "JE-DRAFT"
    assert any(item["code"] == "unposted_journals" for item in body["close_blockers"])
    assert body["project_margin_highlights"][0]["risk_level"] == "high"
    assert body["utilization_highlights"][0]["risk_level"] == "low_utilization"
    assert body["working_capital_movement"]["period_ar_activity"]["current"] == "10000.00"
    assert body["working_capital_movement"]["period_ap_activity"]["current"] == "6500.00"
    assert any("Period is locked" in item for item in body["recommended_next_actions"])
    assert "Foreign tenant journal" not in str(body)


def test_r2r_management_pack_read_pack_handles_no_data_and_missing_tasks() -> None:
    db = _R2RNoDataDb()
    _install_common_overrides()
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: db

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/agents/r2r/management-pack/read-pack?period=2026-06"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data_availability"]["status"] == "no_activity"
    assert body["close_task_checklist_state"]["status"] == "not_bootstrapped"
    assert any(item["code"] == "close_tasks_not_bootstrapped" for item in body["close_blockers"])
    assert body["journal_summary"]["total_count"] == 0
    assert body["financial_statements"]["current"]["trial_balance"]["line_count"] == 0
    assert "Foreign tenant secret journal" not in str(body)
