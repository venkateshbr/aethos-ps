"""Tests for Atlas internal tool-call context references."""

from __future__ import annotations

import pytest

from app.services import atlas_context

pytestmark = pytest.mark.unit


def test_atlas_context_ref_round_trips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(atlas_context.settings, "atlas_context_signing_secret", "secret")

    context_ref = atlas_context.create_atlas_context_ref(
        tenant_id="tenant-1",
        user_id="user-1",
        thread_id="thread-1",
        now=100,
    )

    context = atlas_context.verify_atlas_context_ref(context_ref, now=101)

    assert context.tenant_id == "tenant-1"
    assert context.user_id == "user-1"
    assert context.thread_id == "thread-1"
    assert context.scope == "atlas_tools:read"


def test_atlas_context_ref_rejects_tampering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(atlas_context.settings, "atlas_context_signing_secret", "secret")

    context_ref = atlas_context.create_atlas_context_ref(
        tenant_id="tenant-1",
        user_id="user-1",
        thread_id="thread-1",
        now=100,
    )
    replacement = "x" if context_ref[-1] != "x" else "y"
    tampered = f"{context_ref[:-1]}{replacement}"

    with pytest.raises(atlas_context.AtlasContextError):
        atlas_context.verify_atlas_context_ref(tampered, now=101)


def test_atlas_context_ref_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(atlas_context.settings, "atlas_context_signing_secret", "secret")

    context_ref = atlas_context.create_atlas_context_ref(
        tenant_id="tenant-1",
        user_id="user-1",
        thread_id="thread-1",
        ttl_seconds=10,
        now=100,
    )

    with pytest.raises(atlas_context.AtlasContextError):
        atlas_context.verify_atlas_context_ref(context_ref, now=111)


def test_atlas_context_requires_signing_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(atlas_context.settings, "atlas_context_signing_secret", "")
    monkeypatch.setattr(atlas_context.settings, "supabase_jwt_secret", "")
    monkeypatch.setattr(atlas_context.settings, "aethos_hermes_tool_token", "")

    with pytest.raises(atlas_context.AtlasContextError):
        atlas_context.create_atlas_context_ref(
            tenant_id="tenant-1",
            user_id="user-1",
            thread_id="thread-1",
        )


# ---------------------------------------------------------------------------
# Server-resolved short session tokens (cts_...) — the durable fix for weaker
# models mangling the long signed context_ref.
# ---------------------------------------------------------------------------


class _FakeExecute:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _FakeQuery:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self._token: str | None = None

    def select(self, *_args, **_kwargs) -> "_FakeQuery":
        return self

    def eq(self, column: str, value: str) -> "_FakeQuery":
        if column == "token":
            self._token = value
        return self

    def limit(self, *_args, **_kwargs) -> "_FakeQuery":
        return self

    def execute(self) -> _FakeExecute:
        rows = [r for r in self._rows if r.get("token") == self._token]
        return _FakeExecute(rows[:1])


class _FakeInsert:
    def __init__(self, rows: list[dict], row: dict) -> None:
        self._rows = rows
        self._row = row

    def execute(self) -> _FakeExecute:
        self._rows.append(dict(self._row))
        return _FakeExecute([self._row])


class _FakeTable:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def insert(self, row: dict) -> _FakeInsert:
        return _FakeInsert(self._rows, row)

    def select(self, *args, **kwargs) -> _FakeQuery:
        return _FakeQuery(self._rows).select(*args, **kwargs)


class _FakeDB:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def table(self, _name: str) -> _FakeTable:
        return _FakeTable(self.rows)


def test_session_token_is_short_and_prefixed() -> None:
    db = _FakeDB()
    token = atlas_context.create_atlas_tool_session(
        db, tenant_id="t-1", user_id="u-1", thread_id="th-1", now=1000
    )
    assert token.startswith("cts_")
    assert atlas_context.is_session_context_ref(token)
    assert not atlas_context.is_session_context_ref("ctx_abc.def")
    # The whole point: far shorter than the legacy signed ref the model mangled.
    assert len(token) < 40


def test_session_token_round_trips() -> None:
    db = _FakeDB()
    token = atlas_context.create_atlas_tool_session(
        db, tenant_id="t-1", user_id="u-1", thread_id="th-1", now=1000
    )
    ctx = atlas_context.resolve_atlas_tool_session(db, token, now=1001)
    assert ctx.tenant_id == "t-1"
    assert ctx.user_id == "u-1"
    assert ctx.thread_id == "th-1"
    assert ctx.scope == "atlas_tools:read"


def test_session_token_unknown_is_rejected() -> None:
    db = _FakeDB()
    with pytest.raises(atlas_context.AtlasContextError):
        atlas_context.resolve_atlas_tool_session(db, "cts_missing", now=1000)


def test_session_token_expired_is_rejected() -> None:
    db = _FakeDB()
    token = atlas_context.create_atlas_tool_session(
        db, tenant_id="t-1", user_id="u-1", thread_id="th-1", ttl_seconds=60, now=1000
    )
    with pytest.raises(atlas_context.AtlasContextError):
        atlas_context.resolve_atlas_tool_session(db, token, now=1000 + 61)


def test_session_token_scope_mismatch_is_rejected() -> None:
    db = _FakeDB()
    token = atlas_context.create_atlas_tool_session(
        db, tenant_id="t-1", user_id="u-1", thread_id="th-1", now=1000
    )
    with pytest.raises(atlas_context.AtlasContextError):
        atlas_context.resolve_atlas_tool_session(
            db, token, required_scope="atlas_tools:propose_write", now=1001
        )
