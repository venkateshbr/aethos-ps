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

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-1"


class _Query:
    def __init__(self, db: _DbBase, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, Any]] = []
        self._in_filters: list[tuple[str, list[Any]]] = []
        self._gte_filters: list[tuple[str, Any]] = []
        self._order_key: str | None = None
        self._order_desc = False
        self._limit: int | None = None
        self._upsert_payload: dict[str, Any] | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def in_(self, key: str, values: list[Any]) -> _Query:
        self._in_filters.append((key, values))
        return self

    def gte(self, key: str, value: Any) -> _Query:
        self._gte_filters.append((key, value))
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
        for key, value in self._gte_filters:
            if row.get(key) < value:
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
    row = {
        "id": "tool-1",
        "tenant_id": TENANT_ID,
        "agent_run_id": "run-1",
        "tool_name": "get_wip",
        "risk_class": "read_only",
        "status": "succeeded",
        "external_tool_call_id": "call-1",
        "input_hash": "tool-input",
        "output_hash": "tool-output",
        "input_snapshot": {"engagement_id": "eng-1"},
        "output_snapshot": {"wip": []},
        "duration_ms": 12,
        "error_message": None,
        "created_at": "2026-06-22T06:00:00Z",
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
                "agent_runs": [_run_row()],
                "agent_tool_invocations": [
                    _tool_row(id="tool-2", status="failed", created_at="2026-06-22T06:00:01Z"),
                    _tool_row(id="tool-1", status="succeeded", created_at="2026-06-22T06:00:00Z"),
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
        super().__init__({"agent_autonomy_settings": []})


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
            candidates_response = client.get(
                "/api/v1/agents/eval-candidates?agent_name=copilot_agent&status=candidate"
            )
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

    assert candidates_response.status_code == 200, candidates_response.text
    assert candidates_response.json()["candidates"][0]["id"] == "candidate-1"


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
