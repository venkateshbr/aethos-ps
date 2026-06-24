"""Unit tests for RBAC role hierarchy.

These tests are pure-Python — no I/O, no DB, no HTTP.
"""

from __future__ import annotations

from typing import ClassVar

import pytest
from starlette.requests import Request

from app.core.auth import CurrentUser
from app.core.rbac import ROLE_HIERARCHY, UserRole, _resolve_role
from app.core.tenant import _VERIFIED_TENANT_ROLE_STATE_KEY, _VERIFIED_TENANT_STATE_KEY

pytestmark = pytest.mark.unit


def test_owner_has_highest_rank() -> None:
    assert ROLE_HIERARCHY[UserRole.owner] > ROLE_HIERARCHY[UserRole.admin]


def test_viewer_has_lowest_rank() -> None:
    assert ROLE_HIERARCHY[UserRole.viewer] < ROLE_HIERARCHY[UserRole.member]


def test_all_roles_in_hierarchy() -> None:
    for role in UserRole:
        assert role in ROLE_HIERARCHY, f"{role!r} missing from ROLE_HIERARCHY"


def test_hierarchy_is_strictly_ordered() -> None:
    """No two roles share the same rank."""
    ranks = list(ROLE_HIERARCHY.values())
    assert len(ranks) == len(set(ranks)), "Duplicate ranks found in ROLE_HIERARCHY"


def test_role_enum_values_are_strings() -> None:
    """Roles must be str enum so they round-trip through JSON cleanly."""
    for role in UserRole:
        assert isinstance(role.value, str)


def test_admin_outranks_manager() -> None:
    assert ROLE_HIERARCHY[UserRole.admin] > ROLE_HIERARCHY[UserRole.manager]


def test_manager_outranks_member() -> None:
    assert ROLE_HIERARCHY[UserRole.manager] > ROLE_HIERARCHY[UserRole.member]


class _Result:
    data: ClassVar[list[dict[str, str]]] = [{"id": "membership-id", "role": "owner"}]


class _Query:
    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def is_(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        return _Result()


class _Db:
    def __init__(self) -> None:
        self.table_calls = 0

    def table(self, _name: str):
        self.table_calls += 1
        return _Query()


class _FlakyQuery(_Query):
    def __init__(self, db: _FlakyDb) -> None:
        self.db = db

    def execute(self):
        self.db.execute_calls += 1
        if self.db.execute_calls == 1:
            raise RuntimeError("transient connection reset")
        return _Result()


class _FlakyDb:
    def __init__(self) -> None:
        self.table_calls = 0
        self.execute_calls = 0

    def table(self, _name: str):
        self.table_calls += 1
        return _FlakyQuery(self)


def _request_with_tenant() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"x-tenant-id", b"11111111-1111-1111-1111-111111111111")],
        }
    )


def test_unknown_explicit_app_role_is_viewer_without_db_fallback() -> None:
    db = _Db()
    role = _resolve_role(
        CurrentUser(
            user_id="owner-id",
            email="owner@example.com",
            role="superduperadmin",
        ),
        _request_with_tenant(),
        db,  # type: ignore[arg-type]
    )

    assert role == UserRole.viewer
    assert db.table_calls == 0


def test_authenticated_supabase_role_uses_membership_fallback() -> None:
    db = _Db()
    role = _resolve_role(
        CurrentUser(
            user_id="owner-id",
            email="owner@example.com",
            role="authenticated",
        ),
        _request_with_tenant(),
        db,  # type: ignore[arg-type]
    )

    assert role == UserRole.owner
    assert db.table_calls == 1


def test_authenticated_supabase_role_uses_request_cached_membership_role() -> None:
    db = _Db()
    request = _request_with_tenant()
    setattr(request.state, _VERIFIED_TENANT_STATE_KEY, "11111111-1111-1111-1111-111111111111")
    setattr(request.state, _VERIFIED_TENANT_ROLE_STATE_KEY, "admin")

    role = _resolve_role(
        CurrentUser(
            user_id="owner-id",
            email="owner@example.com",
            role="authenticated",
        ),
        request,
        db,  # type: ignore[arg-type]
    )

    assert role == UserRole.admin
    assert db.table_calls == 0


def test_authenticated_supabase_role_retries_transient_membership_lookup() -> None:
    db = _FlakyDb()

    role = _resolve_role(
        CurrentUser(
            user_id="owner-id",
            email="owner@example.com",
            role="authenticated",
        ),
        _request_with_tenant(),
        db,  # type: ignore[arg-type]
    )

    assert role == UserRole.owner
    assert db.execute_calls == 2
