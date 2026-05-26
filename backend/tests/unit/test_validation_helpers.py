"""Unit tests for app.services._validation (bug #92 — FK tenant validation).

Tests are pure unit (no Supabase) — we stub the db client with a tiny fake
that mirrors the supabase-py builder chain we actually use:
    db.table(t).select("id").eq("id", id).eq("tenant_id", t).limit(1).execute()

Covers:
- belongs to tenant → no raise
- belongs to different tenant → raises 404
- soft-deleted in same tenant → raises 404
- table without deleted_at column (e.g. employees) → still works
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fake supabase-py builder chain
# ---------------------------------------------------------------------------


@dataclass
class _FakeResult:
    data: list[dict]


@dataclass
class _FakeQuery:
    """Records the builder calls and returns a configured row set."""

    rows: list[dict] = field(default_factory=list)
    raise_on_is_null: bool = False  # simulate tables without deleted_at column
    calls: list[tuple[str, tuple, dict]] = field(default_factory=list)
    soft_deleted_rows: list[dict] = field(default_factory=list)

    def select(self, *a, **kw) -> _FakeQuery:
        self.calls.append(("select", a, kw))
        return self

    def eq(self, *a, **kw) -> _FakeQuery:
        self.calls.append(("eq", a, kw))
        return self

    def limit(self, *a, **kw) -> _FakeQuery:
        self.calls.append(("limit", a, kw))
        return self

    def is_(self, *a, **kw) -> _FakeQuery:
        self.calls.append(("is_", a, kw))
        if self.raise_on_is_null:
            raise RuntimeError("simulated: table has no deleted_at column")
        # Mark that we've filtered soft-deletes — strip them.
        if a == ("deleted_at", "null"):
            self.rows = [r for r in self.rows if not r.get("deleted_at")]
        return self

    def execute(self) -> _FakeResult:
        self.calls.append(("execute", (), {}))
        return _FakeResult(data=self.rows)


@dataclass
class _FakeClient:
    queries: dict[str, _FakeQuery] = field(default_factory=dict)

    def table(self, name: str) -> _FakeQuery:
        return self.queries.setdefault(name, _FakeQuery())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


def test_assert_belongs_to_tenant_passes_when_row_exists():
    from app.services._validation import assert_belongs_to_tenant

    db = _FakeClient()
    db.queries["clients"] = _FakeQuery(rows=[{"id": "client-1"}])

    # Should not raise
    asyncio.run(
        assert_belongs_to_tenant(db, "clients", "client-1", "tenant-A")
    )


def test_assert_belongs_to_tenant_raises_404_when_row_missing():
    from app.services._validation import assert_belongs_to_tenant

    db = _FakeClient()
    db.queries["clients"] = _FakeQuery(rows=[])  # row does not exist in this tenant

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            assert_belongs_to_tenant(
                db,
                "clients",
                "client-foreign",
                "tenant-A",
                not_found_detail="Client not found",
            )
        )
    assert exc_info.value.status_code == 404
    assert "Client not found" in exc_info.value.detail


def test_assert_belongs_to_tenant_uses_404_not_403_for_cross_tenant():
    """Information-hiding: the requester must not learn that the id exists elsewhere."""
    from app.services._validation import assert_belongs_to_tenant

    db = _FakeClient()
    # Row exists but in a different tenant — our query filters by tenant_id,
    # so the fake returns an empty result.
    db.queries["clients"] = _FakeQuery(rows=[])

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            assert_belongs_to_tenant(db, "clients", "client-x", "tenant-A")
        )
    assert exc_info.value.status_code == 404
    # Critical: do NOT use 403, that would confirm existence.
    assert exc_info.value.status_code != 403


def test_assert_belongs_to_tenant_excludes_soft_deleted_rows():
    """A row in the same tenant but soft-deleted is treated as not-found."""
    from app.services._validation import assert_belongs_to_tenant

    db = _FakeClient()
    db.queries["clients"] = _FakeQuery(
        rows=[{"id": "client-1", "deleted_at": "2026-05-22T00:00:00Z"}]
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            assert_belongs_to_tenant(db, "clients", "client-1", "tenant-A")
        )
    assert exc_info.value.status_code == 404


def test_assert_belongs_to_tenant_falls_back_for_tables_without_deleted_at():
    """Tables like ``employees`` that have no deleted_at column should still work."""
    from app.services._validation import assert_belongs_to_tenant

    db = _FakeClient()
    db.queries["employees"] = _FakeQuery(
        rows=[{"id": "emp-1"}],
        raise_on_is_null=True,  # simulate column does not exist
    )

    # Should not raise — the helper retries without the soft-delete filter.
    asyncio.run(
        assert_belongs_to_tenant(db, "employees", "emp-1", "tenant-A")
    )


def test_assert_belongs_to_tenant_default_detail_message():
    """Default detail singularises the table name."""
    from app.services._validation import assert_belongs_to_tenant

    db = _FakeClient()
    db.queries["engagements"] = _FakeQuery(rows=[])

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            assert_belongs_to_tenant(db, "engagements", "eng-1", "tenant-A")
        )
    assert "Engagement" in exc_info.value.detail
