"""Chat API contract tests for RLS-backed reads and service-role writes."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
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
        self._update_payload: dict[str, Any] | None = None

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

    def update(self, payload: dict[str, Any]) -> _Query:
        self._update_payload = dict(payload)
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

        if self._update_payload is not None:
            updated: list[dict[str, Any]] = []
            for row in self.db.tables[self.table]:
                if self._matches(row):
                    row.update(self._update_payload)
                    updated.append(row)
            return _Result(deepcopy(updated))

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

    async def _build_runtime(**kwargs: Any) -> _Runtime:
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
    assert write_db.tables["chat_threads"][0]["title"] == "Runtime thread"
    assert write_db.tables["chat_threads"][0]["updated_at"] != "2026-06-22T01:00:00+00:00"


def test_chat_message_stream_uses_deterministic_response_before_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.api.v1.endpoints.chat as chat_module

    write_db = _ChatWriteDb()

    async def _render_semantic(**kwargs: Any) -> SimpleNamespace:
        assert kwargs["db"] is write_db
        assert kwargs["tenant_id"] == TENANT_ID
        assert kwargs["current_user"].user_id == USER_ID
        assert kwargs["thread_id"] == "thread-1"
        assert "COSEC" in kwargs["message"]
        assert kwargs["min_confidence"] == 0.72
        return SimpleNamespace(
            text="COSEC reminders require Inbox approval before sending.",
            route=SimpleNamespace(
                intent="cosec_reminders",
                confidence=0.91,
                action_mode="read",
            ),
        )

    async def _build_runtime(**_kwargs: Any) -> None:
        raise AssertionError("runtime should not be built for deterministic Atlas response")

    monkeypatch.setattr(
        chat_module,
        "render_semantic_atlas_response",
        _render_semantic,
    )
    monkeypatch.setattr(chat_module, "build_atlas_runtime", _build_runtime)

    _install_common_overrides()
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: write_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat/threads/thread-1/messages",
                json={"content": "Review COSEC reminders"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert "COSEC reminders require Inbox approval" in response.text
    assert '"tool_start"' not in response.text
    assert '"tool_result"' not in response.text
    messages = write_db.tables["chat_messages"]
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "COSEC reminders require Inbox approval before sending."
    assert messages[1]["model"] == "aethos-semantic-intent"


def test_chat_message_stream_emits_semantic_tool_frames_before_delta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.api.v1.endpoints.chat as chat_module

    write_db = _ChatWriteDb()

    async def _render_semantic(**kwargs: Any) -> SimpleNamespace:
        assert kwargs["db"] is write_db
        assert kwargs["tenant_id"] == TENANT_ID
        assert kwargs["current_user"].user_id == USER_ID
        assert kwargs["thread_id"] == "thread-1"
        return SimpleNamespace(
            text="Prepared the time entry and routed it to Inbox for review.",
            tool_name="log_time_entry",
            route=SimpleNamespace(
                intent="time_log",
                confidence=0.94,
                action_mode="prepare",
            ),
        )

    async def _build_runtime(**_kwargs: Any) -> None:
        raise AssertionError("runtime should not be built for deterministic Atlas response")

    monkeypatch.setattr(
        chat_module,
        "render_semantic_atlas_response",
        _render_semantic,
    )
    monkeypatch.setattr(chat_module, "build_atlas_runtime", _build_runtime)

    _install_common_overrides()
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: write_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat/threads/thread-1/messages",
                json={
                    "content": (
                        'Log exactly 4.5 billable hours on project "Nexus Advisory" '
                        'for 2026-07-11. Use this exact description: "Board pack review".'
                    )
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    events = [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    assert events == [
        {"tool_start": "log_time_entry"},
        {"tool_result": "log_time_entry"},
        {"delta": "Prepared the time entry and routed it to Inbox for review."},
        {"done": True, "finish_reason": "stop"},
    ]

    messages = write_db.tables["chat_messages"]
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == (
        "Prepared the time entry and routed it to Inbox for review."
    )
    assert messages[1]["model"] == "aethos-semantic-intent"


@pytest.mark.asyncio
async def test_deterministic_manual_journal_honors_explicit_gbp_base_currency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import atlas_deterministic_responses as deterministic

    calls: list[dict[str, Any]] = []

    async def _prepare_manual_journal_review(
        db: object,
        context: object,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        calls.append(arguments)
        return {
            "requested_transaction": {
                "currency": "SGD",
                "amount": "18000.00",
                "base_currency": arguments["base_currency"],
                "base_amount": "10533.60",
                "fx_rate_provenance": "SGD->GBP rate 0.5852 from fx_rates dated 2026-05-19.",
            },
            "review_path": "/app/inbox",
            "task_id": "task-gbp",
            "approval_boundary": "Do not post without Inbox approval.",
            "journal_lines": [
                {
                    "direction": "DR",
                    "account_code": "1100",
                    "account_name": "Bank",
                    "currency": "SGD",
                    "amount": "18000.00",
                    "base_amount": "10533.60",
                },
                {
                    "direction": "CR",
                    "account_code": "4000",
                    "account_name": "Revenue",
                    "currency": "SGD",
                    "amount": "18000.00",
                    "base_amount": "10533.60",
                },
            ],
            "control_checks": {
                "balance": {
                    "balanced": True,
                    "debits": "18000.00",
                    "credits": "18000.00",
                },
                "account_validity": {"status": "valid"},
                "period_lock_status": {"status": "open"},
                "business_reason": "Record foreign dividend income.",
                "supporting_evidence": "Dividend notice required.",
                "required_approval_role": "finance_controller",
                "segregation_of_duties": "Approver must be different from the submitter.",
            },
        }

    monkeypatch.setattr(
        deterministic.atlas_tools,
        "_prepare_manual_journal_review",
        _prepare_manual_journal_review,
    )

    answer = await deterministic.render_deterministic_atlas_response(
        db=object(),
        tenant_id=TENANT_ID,
        current_user=CurrentUser(
            user_id=USER_ID,
            email="manager@example.com",
            role="manager",
        ),
        thread_id="thread-1",
        message=(
            "Prepare an SGD 18,000 dividend income journal for Alderton Trust for "
            "June 2026. Show the GBP base-currency impact, FX rate provenance, "
            "required approval role, and route it to Inbox before posting."
        ),
    )

    assert calls[0]["base_currency"] == "GBP"
    assert answer is not None
    assert "SGD 18000.00" in answer
    assert "GBP base-currency impact 10533.60" in answer
    assert "SGD->GBP rate" in answer
    assert "Inbox" in answer


def test_first_user_message_names_blank_chat_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.api.v1.endpoints.chat as chat_module

    write_db = _ChatWriteDb()
    write_db.tables["chat_threads"][0]["title"] = "New conversation"

    class _Runtime:
        async def stream_message(self, *, user_message: str, thread_id: str):
            assert user_message == "Show me active engagements"
            assert thread_id == "thread-1"
            yield 'data: {"delta":"Nexus has active work."}\n\n'
            yield 'data: {"done":true,"finish_reason":"stop"}\n\n'

    async def _build_runtime(**_kwargs: Any) -> _Runtime:
        return _Runtime()

    monkeypatch.setattr(chat_module, "build_atlas_runtime", _build_runtime)

    _install_common_overrides()
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: write_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat/threads/thread-1/messages",
                json={"content": "Show me active engagements"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert write_db.tables["chat_threads"][0]["title"] == "Show me active engagements"
