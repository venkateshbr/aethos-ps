"""Chat API contract tests for RLS-backed reads and service-role writes."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.tenant import get_tenant_id
from app.main import app

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-1"
USER_ID = "user-1"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _DbBase, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, Any]] = []
        self._null_filters: list[str] = []
        self._order_key: str | None = None
        self._order_desc = False
        self._limit: int | None = None
        self._insert_payload: dict[str, Any] | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def is_(self, key: str, value: Any) -> _Query:
        if value == "null":
            self._null_filters.append(key)
        return self

    def order(self, key: str, desc: bool = False) -> _Query:
        self._order_key = key
        self._order_desc = desc
        return self

    def limit(self, limit: int) -> _Query:
        self._limit = limit
        return self

    def insert(self, payload: dict[str, Any]) -> _Query:
        self._insert_payload = dict(payload)
        return self

    def execute(self) -> _Result:
        if self._insert_payload is not None:
            row = {
                "id": "thread-created",
                "title": None,
                "created_at": "2026-06-22T00:00:00+00:00",
                "updated_at": "2026-06-22T00:00:00+00:00",
                "deleted_at": None,
                **self._insert_payload,
            }
            self.db.tables[self.table].append(row)
            return _Result([deepcopy(row)])

        rows = [row for row in self.db.tables[self.table] if self._matches(row)]
        if self._order_key is not None:
            rows.sort(
                key=lambda row: str(row.get(self._order_key) or ""),
                reverse=self._order_desc,
            )
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Result(deepcopy(rows))

    def _matches(self, row: dict[str, Any]) -> bool:
        for key, value in self._eq_filters:
            if row.get(key) != value:
                return False
        for key in self._null_filters:
            if row.get(key) is not None:
                return False
        return True


class _DbBase:
    def __init__(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        self.tables = tables

    def table(self, name: str) -> _Query:
        assert name in self.tables
        return _Query(self, name)


class _ReadDb(_DbBase):
    def __init__(self) -> None:
        super().__init__(
            {
                "chat_threads": [
                    {
                        "id": "thread-1",
                        "tenant_id": TENANT_ID,
                        "user_id": USER_ID,
                        "title": "Revenue question",
                        "created_at": "2026-06-22T00:00:00+00:00",
                        "updated_at": "2026-06-22T01:00:00+00:00",
                        "deleted_at": None,
                    }
                ],
                "chat_messages": [
                    {
                        "id": "message-1",
                        "tenant_id": TENANT_ID,
                        "thread_id": "thread-1",
                        "role": "user",
                        "content": "What needs billing?",
                        "tool_name": None,
                        "finish_reason": None,
                        "model": None,
                        "usage_input_tokens": None,
                        "usage_output_tokens": None,
                        "created_at": "2026-06-22T00:05:00+00:00",
                    },
                    {
                        "id": "message-2",
                        "tenant_id": TENANT_ID,
                        "thread_id": "thread-1",
                        "role": "assistant",
                        "content": "Nexus has WIP to review.",
                        "tool_name": None,
                        "finish_reason": "stop",
                        "model": "test-model",
                        "usage_input_tokens": None,
                        "usage_output_tokens": None,
                        "created_at": "2026-06-22T00:06:00+00:00",
                    },
                ],
            }
        )


class _WriteDb(_DbBase):
    def __init__(self) -> None:
        super().__init__({"chat_threads": []})


class _ChatWriteDb(_DbBase):
    def __init__(self) -> None:
        super().__init__(
            {
                "chat_threads": [
                    {
                        "id": "thread-1",
                        "tenant_id": TENANT_ID,
                        "user_id": USER_ID,
                        "title": "Runtime thread",
                        "created_at": "2026-06-22T00:00:00+00:00",
                        "updated_at": "2026-06-22T01:00:00+00:00",
                        "deleted_at": None,
                    }
                ],
                "chat_messages": [],
            }
        )


class _ForbiddenDb:
    def table(self, name: str) -> None:
        raise AssertionError(f"wrong dependency attempted to access {name}")


def _install_common_overrides() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=USER_ID,
        email="manager@example.com",
        role="manager",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID


def test_chat_thread_list_uses_rls_client() -> None:
    _install_common_overrides()
    app.dependency_overrides[get_user_rls_client] = lambda: _ReadDb()
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/chat/threads?limit=10")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()[0]["id"] == "thread-1"
    assert response.json()[0]["tenant_id"] == TENANT_ID


def test_chat_thread_create_uses_service_role_client() -> None:
    write_db = _WriteDb()
    _install_common_overrides()
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: write_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat/threads",
                json={"title": "Created thread"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201, response.text
    assert response.json()["id"] == "thread-created"
    assert write_db.tables["chat_threads"][0]["tenant_id"] == TENANT_ID
    assert write_db.tables["chat_threads"][0]["user_id"] == USER_ID


def test_chat_message_list_uses_rls_client_and_returns_history() -> None:
    _install_common_overrides()
    app.dependency_overrides[get_user_rls_client] = lambda: _ReadDb()
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/chat/threads/thread-1/messages?limit=10")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    rows = response.json()
    assert [row["role"] for row in rows] == ["user", "assistant"]
    assert rows[0]["content"] == "What needs billing?"
    assert rows[1]["content"] == "Nexus has WIP to review."


def test_chat_messages_authenticated_read_rls_scopes_to_owned_threads() -> None:
    migration = (
        Path(__file__).parents[2]
        / "supabase/migrations/0092_chat_messages_authenticated_read_rls.sql"
    )
    sql = migration.read_text()

    assert 'CREATE POLICY "authenticated_owner_read" ON chat_messages' in sql
    assert "FOR SELECT" in sql
    assert "TO authenticated" in sql
    assert "public.is_tenant_member(auth.uid(), tenant_id)" in sql
    assert "chat_threads.id = chat_messages.thread_id" in sql
    assert "chat_threads.tenant_id = chat_messages.tenant_id" in sql
    assert "chat_threads.user_id = auth.uid()" in sql
    assert "chat_threads.deleted_at IS NULL" in sql


def test_chat_message_stream_uses_runtime_interface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.api.v1.endpoints.chat as chat_module

    write_db = _ChatWriteDb()

    class _Runtime:
        async def stream_message(self, *, user_message: str, thread_id: str):
            assert user_message == "hello Atlas"
            assert thread_id == "thread-1"
            yield 'data: {"delta":"Runtime reply"}\n\n'
            yield 'data: {"done":true,"finish_reason":"stop"}\n\n'

    def _build_runtime(**kwargs: Any) -> _Runtime:
        assert kwargs["tenant_id"] == TENANT_ID
        assert kwargs["user_id"] == USER_ID
        assert kwargs["db_client"] is write_db
        return _Runtime()

    monkeypatch.setattr(chat_module, "build_atlas_runtime", _build_runtime)

    _install_common_overrides()
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: write_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat/threads/thread-1/messages",
                json={"content": "hello Atlas"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert "Runtime reply" in response.text
    messages = write_db.tables["chat_messages"]
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "hello Atlas"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Runtime reply"
