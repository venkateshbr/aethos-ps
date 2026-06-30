"""Approval policy API contract tests."""

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
    def __init__(self, db: _Db, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, Any]] = []
        self._upsert_payload: dict[str, Any] | None = None
        self._limit: int | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def limit(self, count: int) -> _Query:
        self._limit = count
        return self

    def upsert(self, payload: dict[str, Any], **_kwargs: Any) -> _Query:
        self._upsert_payload = dict(payload)
        return self

    def execute(self) -> _Result:
        if self._upsert_payload is not None:
            payload = dict(self._upsert_payload)
            rows = self.db.tables[self.table]
            existing = next(
                (row for row in rows if row.get("tenant_id") == payload.get("tenant_id")),
                None,
            )
            if existing:
                existing.update(payload)
                row = existing
            else:
                payload.setdefault("created_at", "2026-06-24T00:00:00+00:00")
                payload.setdefault("updated_at", "2026-06-24T00:00:00+00:00")
                rows.append(payload)
                row = payload
            return _Result([deepcopy(row)])

        rows = list(self.db.tables[self.table])
        for key, value in self._eq_filters:
            rows = [row for row in rows if row.get(key) == value]
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Result(deepcopy(rows))


class _Db:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "tenant_approval_policies": []
        }

    def table(self, name: str) -> _Query:
        return _Query(self, name)


class _ForbiddenDb:
    def table(self, name: str) -> None:
        raise AssertionError(f"wrong dependency attempted to access {name}")


def _install_overrides(*, role: str, read_db: object, write_db: object) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=f"{role}-1",
        email=f"{role}@example.com",
        role=role,
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: read_db
    app.dependency_overrides[get_service_role_client] = lambda: write_db


def test_manager_can_read_default_approval_policy() -> None:
    read_db = _Db()
    _install_overrides(role="manager", read_db=read_db, write_db=_ForbiddenDb())

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/approval-policy/effective")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tenant_id"] == TENANT_ID
    assert body["policy_source"] == "system_default"
    assert body["money_out_default_role"] == "admin"
    assert body["money_out_owner_threshold"] == "50000"
    assert body["manual_journal_approval_threshold"] == "10000"


def test_admin_can_save_tenant_approval_policy_with_service_role_client() -> None:
    write_db = _Db()
    _install_overrides(role="admin", read_db=_ForbiddenDb(), write_db=write_db)

    try:
        with TestClient(app) as client:
            response = client.put(
                "/api/v1/approval-policy/default",
                json={
                    "money_out_default_role": "owner",
                    "money_out_owner_threshold": "25000",
                    "money_out_owner_role": "owner",
                    "accounting_role": "owner",
                    "manual_journal_approval_threshold": "15000",
                    "money_in_role": "approver",
                    "draft_role": "approver",
                    "external_send_role": "admin",
                    "high_risk_role": "owner",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["policy_source"] == "tenant_default"
    assert body["money_out_default_role"] == "owner"
    assert body["manual_journal_approval_threshold"] == "15000"
    assert body["money_in_role"] == "approver"
    assert body["draft_role"] == "approver"
    assert body["external_send_role"] == "admin"
    assert write_db.tables["tenant_approval_policies"][0]["tenant_id"] == TENANT_ID


def test_approval_policy_rejects_unsafe_downgrade() -> None:
    write_db = _Db()
    _install_overrides(role="admin", read_db=_ForbiddenDb(), write_db=write_db)

    try:
        with TestClient(app) as client:
            response = client.put(
                "/api/v1/approval-policy/default",
                json={
                    "money_out_default_role": "manager",
                    "money_out_owner_threshold": "50000",
                    "money_out_owner_role": "owner",
                    "accounting_role": "admin",
                    "manual_journal_approval_threshold": "10000",
                    "money_in_role": "manager",
                    "draft_role": "manager",
                    "external_send_role": "manager",
                    "high_risk_role": "admin",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert write_db.tables["tenant_approval_policies"] == []
