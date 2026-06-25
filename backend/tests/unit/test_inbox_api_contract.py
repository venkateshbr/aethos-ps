"""Inbox API contract tests for RLS-backed reads and service-role actions."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.tenant import get_tenant_id
from app.main import app

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-123"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _FakeDb, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, Any]] = []
        self._order_key: str | None = None
        self._order_desc = False
        self._limit: int | None = None
        self._update_payload: dict[str, Any] | None = None
        self._insert_payload: dict[str, Any] | None = None
        self._upsert_payload: dict[str, Any] | None = None
        self._in_filters: list[tuple[str, set[Any]]] = []

    def select(self, *_args: Any, **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def in_(self, key: str, values: list[Any]) -> _Query:
        self._in_filters.append((key, set(values)))
        return self

    def is_(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, None if value == "null" else value))
        return self

    def order(self, key: str, *, desc: bool = False) -> _Query:
        self._order_key = key
        self._order_desc = desc
        return self

    def limit(self, limit: int) -> _Query:
        self._limit = limit
        return self

    def update(self, payload: dict[str, Any]) -> _Query:
        self._update_payload = dict(payload)
        return self

    def insert(self, payload: dict[str, Any]) -> _Query:
        self._insert_payload = dict(payload)
        return self

    def upsert(self, payload: dict[str, Any], **_kwargs: Any) -> _Query:
        self._upsert_payload = dict(payload)
        return self

    def execute(self) -> _Result:
        if self._insert_payload is not None:
            payload = dict(self._insert_payload)
            payload.setdefault("id", f"{self.table}-{len(self.db.tables[self.table]) + 1}")
            self.db.tables[self.table].append(payload)
            if self.table == "agent_suggestions":
                self.db.suggestion_by_id[str(payload["id"])] = payload
            return _Result([deepcopy(payload)])

        if self._upsert_payload is not None:
            payload = dict(self._upsert_payload)
            payload.setdefault("id", f"{self.table}-{len(self.db.tables[self.table]) + 1}")
            self.db.tables[self.table].append(payload)
            return _Result([deepcopy(payload)])

        rows = self._filtered_rows()
        if self._update_payload is not None:
            if self.table == "financial_events":
                raise AssertionError("financial_events must not be updated")
            for row in rows:
                row.update(self._update_payload)
            return _Result(deepcopy(rows))

        rows = [self._with_embeds(row) for row in rows]
        if self._order_key is not None:
            rows.sort(
                key=lambda row: str(row.get(self._order_key) or ""),
                reverse=self._order_desc,
            )
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Result(deepcopy(rows))

    def _filtered_rows(self) -> list[dict[str, Any]]:
        rows = list(self.db.tables[self.table])
        for key, value in self._eq_filters:
            rows = [row for row in rows if row.get(key) == value]
        for key, values in self._in_filters:
            rows = [row for row in rows if row.get(key) in values]
        return rows

    def _with_embeds(self, row: dict[str, Any]) -> dict[str, Any]:
        result = dict(row)
        if self.table == "hitl_tasks":
            suggestion_id = result.get("agent_suggestion_id")
            result["agent_suggestions"] = self.db.suggestion_by_id.get(str(suggestion_id))
        return result


class _FakeDb:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "agent_suggestions": [
                {
                    "id": "suggestion-1",
                    "tenant_id": TENANT_ID,
                    "agent_name": "vendor_invoice_agent",
                    "confidence": "0.88",
                    "output_snapshot": {"vendor_name": "Acme Supplies"},
                    "action_type": "create_bill",
                    "status": "pending",
                }
            ],
            "hitl_tasks": [
                {
                    "id": "task-1",
                    "tenant_id": TENANT_ID,
                    "kind": "create_bill",
                    "priority": "normal",
                    "title": "Review vendor bill",
                    "description": "Verify extracted bill fields",
                    "payload": {"source": "document-1"},
                    "status": "open",
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "updated_at": "2026-06-22T00:00:00+00:00",
                    "agent_suggestion_id": "suggestion-1",
                }
            ],
            "tenant_users": [
                {"tenant_id": TENANT_ID, "user_id": "owner-1", "role": "owner"},
                {
                    "tenant_id": TENANT_ID,
                    "user_id": "user-1",
                    "role": "manager",
                    "deleted_at": None,
                },
            ],
            "financial_events": [],
            "agent_corrections": [],
            "agent_eval_candidates": [],
            "tenant_approval_policies": [],
        }
        self.suggestion_by_id = {
            str(row["id"]): row for row in self.tables["agent_suggestions"]
        }

    def table(self, name: str) -> _Query:
        return _Query(self, name)

    def rpc(self, name: str, params: dict[str, Any]) -> _Query:
        if name != "append_financial_event":
            raise AssertionError(f"unexpected rpc {name}")
        event = {
            "id": f"event-{len(self.tables['financial_events']) + 1}",
            "tenant_id": params["p_tenant_id"],
            "event_type": params["p_event_type"],
            "entity_type": params["p_entity_type"],
            "entity_id": params["p_entity_id"],
            "source_type": params["p_source_type"],
            "source_id": params["p_source_id"],
            "actor_user_id": params["p_actor_user_id"],
            "actor_role": params["p_actor_role"],
            "action": params["p_action"],
            "before_state": params["p_before_state"],
            "after_state": params["p_after_state"],
            "metadata": params["p_metadata"],
            "idempotency_key": params["p_idempotency_key"],
            "previous_event_hash": None,
            "event_hash": f"hash-event-{len(self.tables['financial_events']) + 1}",
            "created_at": "2026-06-24T00:00:00+00:00",
        }
        self.tables["financial_events"].append(event)
        return _RpcResult(event)


class _RpcResult:
    def __init__(self, row: dict[str, Any]) -> None:
        self.row = row

    def execute(self) -> _Result:
        return _Result([deepcopy(self.row)])


class _ForbiddenDb:
    def table(self, name: str) -> None:
        raise AssertionError(f"wrong dependency attempted to access {name}")


@pytest.fixture
def fake_db() -> _FakeDb:
    return _FakeDb()


@pytest.fixture
def client(fake_db: _FakeDb) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="manager@example.com",
        role="manager",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_inbox_read_routes_use_rls_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    list_response = client.get("/api/v1/inbox/tasks?status=open&kind=create_bill")
    detail_response = client.get("/api/v1/inbox/tasks/task-1")

    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["tenant_id"] == TENANT_ID
    assert list_response.json()["items"][0]["agent_name"] == "vendor_invoice_agent"
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["tenant_id"] == TENANT_ID
    assert detail_response.json()["payload"] == {"source": "document-1"}
    assert detail_response.json()["required_approval_role"] == "manager"


def test_viewer_can_read_inbox_but_cannot_decide(
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="auditor-1",
        email="auditor@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    try:
        with TestClient(app) as viewer_client:
            list_response = viewer_client.get("/api/v1/inbox/tasks")
            approve_response = viewer_client.post("/api/v1/inbox/tasks/task-1/approve")
            edit_response = viewer_client.post(
                "/api/v1/inbox/tasks/task-1/approve-with-edits",
                json={"corrected_payload": {"vendor_name": "Blocked Edit"}},
            )
            reject_response = viewer_client.post(
                "/api/v1/inbox/tasks/task-1/reject",
                json={"reason": "viewer cannot reject"},
            )
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["total"] == 1
    assert approve_response.status_code == 403, approve_response.text
    assert edit_response.status_code == 403, edit_response.text
    assert reject_response.status_code == 403, reject_response.text
    assert fake_db.tables["hitl_tasks"][0]["status"] == "open"
    assert fake_db.tables["agent_suggestions"][0]["status"] == "pending"


def test_inbox_tasks_expose_enterprise_approval_policy(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    fake_db.tables["agent_suggestions"][0]["output_snapshot"] = {
        "risk_class": "write_money_out",
        "total_amount": "75000.00",
    }
    fake_db.tables["hitl_tasks"][0].update(
        {
            "kind": "create_bill_payment_batch",
            "payload": {"total_amount": "75000.00"},
        }
    )

    response = client.get("/api/v1/inbox/tasks/task-1")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["required_approval_role"] == "owner"
    assert body["approval_policy_reason"] == "money_out_above_owner_review_threshold"
    assert body["approval_policy"]["threshold"] == "50000"


def test_inbox_tasks_use_tenant_approval_policy_override(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    fake_db.tables["tenant_approval_policies"].append(
        {
            "tenant_id": TENANT_ID,
            "money_out_default_role": "owner",
            "money_out_owner_threshold": "25000.00",
            "money_out_owner_role": "owner",
            "accounting_role": "admin",
            "money_in_role": "manager",
            "draft_role": "manager",
            "external_send_role": "admin",
            "high_risk_role": "admin",
        }
    )
    fake_db.tables["hitl_tasks"][0].update(
        {
            "kind": "send_email",
            "payload": {"subject": "Collection reminder"},
        }
    )

    response = client.get("/api/v1/inbox/tasks/task-1")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["required_approval_role"] == "admin"
    assert body["approval_policy_reason"] == "external_send_requires_review"


def test_inbox_approval_denies_user_below_required_policy_role(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    fake_db.tables["agent_suggestions"][0]["output_snapshot"] = {
        "risk_class": "write_money_out",
        "total_amount": "75000.00",
    }
    fake_db.tables["hitl_tasks"][0].update(
        {
            "kind": "create_bill_payment_batch",
            "payload": {
                "total_amount": "75000.00",
                "proposed_bill_ids": ["bill-1"],
            },
        }
    )

    response = client.post("/api/v1/inbox/tasks/task-1/approve")

    assert response.status_code == 403, response.text
    assert "requires owner or higher" in response.json()["detail"]
    assert fake_db.tables["hitl_tasks"][0]["status"] == "open"
    assert fake_db.tables["agent_suggestions"][0]["status"] == "pending"
    event = fake_db.tables["financial_events"][0]
    assert event["event_type"] == "hitl_task.approval_denied"
    assert event["action"] == "approve_denied"
    assert event["entity_type"] == "hitl_task"
    assert event["entity_id"] == "task-1"
    assert event["metadata"]["decision_result"] == "denied"
    assert event["metadata"]["policy"]["required_role"] == "owner"


def test_inbox_approve_with_edits_evaluates_corrected_payload_policy(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    fake_db.tables["agent_suggestions"][0]["output_snapshot"] = {
        "risk_class": "write_money_out",
        "total_amount": "1000.00",
    }
    fake_db.tables["hitl_tasks"][0].update(
        {
            "kind": "create_bill_payment_batch",
            "payload": {
                "risk_class": "write_money_out",
                "total_amount": "1000.00",
                "proposed_bill_ids": ["bill-1"],
            },
        }
    )

    response = client.post(
        "/api/v1/inbox/tasks/task-1/approve-with-edits",
        json={
            "corrected_payload": {
                "risk_class": "write_money_out",
                "total_amount": "75000.00",
                "proposed_bill_ids": ["bill-1"],
            }
        },
    )

    assert response.status_code == 403, response.text
    assert "requires owner or higher" in response.json()["detail"]
    assert fake_db.tables["hitl_tasks"][0]["status"] == "open"
    event = fake_db.tables["financial_events"][0]
    assert event["event_type"] == "hitl_task.approval_denied"
    assert event["action"] == "approve_with_edits_denied"


def test_inbox_approval_writes_decision_audit_event(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    fake_db.tables["hitl_tasks"][0]["kind"] = "review_note"

    response = client.post("/api/v1/inbox/tasks/task-1/approve")

    assert response.status_code == 200, response.text
    assert fake_db.tables["hitl_tasks"][0]["status"] == "done"
    assert fake_db.tables["agent_suggestions"][0]["status"] == "approved"
    event = fake_db.tables["financial_events"][0]
    assert event["event_type"] == "hitl_task.approved"
    assert event["action"] == "approved"
    assert event["actor_user_id"] == "user-1"
    assert event["actor_role"] == "manager"
    assert event["source_type"] == "agent_suggestion"
    assert event["source_id"] == "suggestion-1"
    assert event["before_state"]["payload"]["vendor_name"] == "Acme Supplies"
    assert event["after_state"]["task"]["status"] == "done"
    assert event["after_state"]["materialisation"]["entity_type"] == "review_note"
    assert event["metadata"]["policy"]["required_role"] == "manager"
    assert event["idempotency_key"] == "hitl_task.approved:task-1"


def test_inbox_approve_with_edits_writes_before_after_audit_event(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    fake_db.tables["hitl_tasks"][0]["kind"] = "review_note"

    response = client.post(
        "/api/v1/inbox/tasks/task-1/approve-with-edits",
        json={"corrected_payload": {"vendor_name": "Acme Corrected"}},
    )

    assert response.status_code == 200, response.text
    assert fake_db.tables["hitl_tasks"][0]["status"] == "done"
    assert fake_db.tables["agent_corrections"][0]["correction_type"] == "edit"
    event = fake_db.tables["financial_events"][0]
    assert event["event_type"] == "hitl_task.approved_with_edits"
    assert event["action"] == "approved_with_edits"
    assert event["before_state"]["payload"]["vendor_name"] == "Acme Supplies"
    assert event["after_state"]["payload"]["vendor_name"] == "Acme Corrected"
    assert event["idempotency_key"] == "hitl_task.approved_with_edits:task-1"


def test_inbox_reject_writes_decision_audit_event(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    fake_db.tables["hitl_tasks"][0]["payload"]["original_document_id"] = "document-1"

    response = client.post(
        "/api/v1/inbox/tasks/task-1/reject",
        json={"reason": "Duplicate vendor invoice"},
    )

    assert response.status_code == 200, response.text
    assert fake_db.tables["hitl_tasks"][0]["status"] == "done"
    assert fake_db.tables["agent_suggestions"][0]["status"] == "rejected"
    assert fake_db.tables["agent_corrections"][0]["correction_type"] == "reject"
    event = fake_db.tables["financial_events"][0]
    assert event["event_type"] == "hitl_task.rejected"
    assert event["action"] == "rejected"
    assert event["after_state"]["payload"]["reason"] == "Duplicate vendor invoice"
    assert event["metadata"]["decision_result"] == "rejected"
    document_event = fake_db.tables["financial_events"][1]
    assert document_event["entity_type"] == "document"
    assert document_event["entity_id"] == "document-1"
    assert document_event["metadata"]["source_hitl_task_id"] == "task-1"


def test_inbox_reject_threshold_manual_journal_writes_lifecycle_event(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    fake_db.tables["agent_suggestions"][0].update(
        {
            "agent_name": "manual_journal_service",
            "action_type": "draft_journal",
            "output_snapshot": {
                "description": "Month-end accrual",
                "reason": "Accrue June payroll based on approved payroll register.",
                "entry_date": "2026-06-22",
                "reference": "ACCRUAL-001",
                "total_debits": "15000.00",
                "lines": [
                    {
                        "direction": "DR",
                        "amount": "15000.00",
                        "currency": "USD",
                    },
                    {
                        "direction": "CR",
                        "amount": "15000.00",
                        "currency": "USD",
                    },
                ],
            },
        }
    )
    fake_db.tables["hitl_tasks"][0].update(
        {
            "kind": "draft_journal",
            "title": "Review high-value manual journal: Month-end accrual",
            "payload": {
                "manual_journal_approval": {
                    "source": "manual_journal_threshold",
                    "submitted_by": "submitter-1",
                    "submitted_by_role": "manager",
                    "threshold": "10000.00",
                }
            },
        }
    )

    response = client.post(
        "/api/v1/inbox/tasks/task-1/reject",
        json={"reason": "Payroll register was not final."},
    )

    assert response.status_code == 200, response.text
    assert fake_db.tables["hitl_tasks"][0]["status"] == "done"
    assert fake_db.tables["agent_suggestions"][0]["status"] == "rejected"
    generic_event = fake_db.tables["financial_events"][0]
    assert generic_event["event_type"] == "hitl_task.rejected"
    event = fake_db.tables["financial_events"][1]
    assert event["event_type"] == "manual_journal.rejected"
    assert event["entity_type"] == "hitl_task"
    assert event["entity_id"] == "task-1"
    assert event["source_type"] == "agent_suggestion"
    assert event["source_id"] == "suggestion-1"
    assert event["action"] == "rejected"
    assert event["metadata"]["reason"].startswith("Accrue June payroll")
    assert event["metadata"]["rejection_reason"] == "Payroll register was not final."
    assert event["metadata"]["total_debits"] == "15000.00"
    assert event["metadata"]["threshold"] == "10000.00"
    assert event["metadata"]["submitted_by"] == "submitter-1"
    assert event["metadata"]["required_role"] == "admin"
    assert event["after_state"]["payload"]["reason"] == "Payroll register was not final."
    assert event["idempotency_key"] == "manual_journal.rejected:task-1"


def test_inbox_done_task_detail_exposes_decision_history(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    fake_db.tables["hitl_tasks"][0]["status"] = "done"
    fake_db.tables["financial_events"].append(
        {
            "id": "event-1",
            "tenant_id": TENANT_ID,
            "event_type": "hitl_task.approved",
            "entity_type": "hitl_task",
            "entity_id": "task-1",
            "source_type": "agent_suggestion",
            "source_id": "suggestion-1",
            "actor_user_id": "user-1",
            "actor_role": "manager",
            "action": "approved",
            "before_state": {},
            "after_state": {"materialisation": {"entity_type": "review_note"}},
            "metadata": {"decision_result": "approved"},
            "idempotency_key": "hitl_task.approved:task-1",
            "previous_event_hash": None,
            "event_hash": "hash-event-1",
            "created_at": "2026-06-24T00:00:00+00:00",
        }
    )

    response = client.get("/api/v1/inbox/tasks/task-1")

    assert response.status_code == 200, response.text
    history = response.json()["decision_history"]
    assert len(history) == 1
    assert history[0]["event_type"] == "hitl_task.approved"
    assert history[0]["event_hash"] == "hash-event-1"


def test_inbox_escalation_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    response = client.post("/api/v1/inbox/tasks/task-1/escalate")

    assert response.status_code == 200, response.text
    assert response.json()["escalated"] is True
    assert fake_db.tables["hitl_tasks"][0]["priority"] == "critical"
    assert fake_db.tables["hitl_tasks"][0]["assigned_to"] == "owner-1"
