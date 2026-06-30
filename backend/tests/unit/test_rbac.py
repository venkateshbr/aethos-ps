"""Unit tests for RBAC role hierarchy.

These tests are pure-Python — no I/O, no DB, no HTTP.
"""

from __future__ import annotations

from typing import ClassVar

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.auth import CurrentUser
from app.core.finance_personas import finance_persona_catalog, persona_ids_for_role
from app.core.rbac import (
    ROLE_HIERARCHY,
    UserRole,
    _resolve_role,
    role_allows_approval,
    role_meets_minimum,
)
from app.core.tenant import (
    _VERIFIED_TENANT_ROLE_STATE_KEY,
    _VERIFIED_TENANT_STATE_KEY,
    get_tenant_id,
)

pytestmark = pytest.mark.unit


def test_owner_has_highest_rank() -> None:
    assert ROLE_HIERARCHY[UserRole.owner] > ROLE_HIERARCHY[UserRole.admin]


def test_viewer_has_lowest_rank() -> None:
    assert ROLE_HIERARCHY[UserRole.viewer] < ROLE_HIERARCHY[UserRole.member]


def test_all_roles_in_hierarchy() -> None:
    for role in UserRole:
        assert role in ROLE_HIERARCHY, f"{role!r} missing from ROLE_HIERARCHY"


def test_auditor_and_viewer_share_read_only_rank() -> None:
    assert ROLE_HIERARCHY[UserRole.auditor] == ROLE_HIERARCHY[UserRole.viewer]
    assert role_meets_minimum(UserRole.auditor, UserRole.viewer)


def test_role_enum_values_are_strings() -> None:
    """Roles must be str enum so they round-trip through JSON cleanly."""
    for role in UserRole:
        assert isinstance(role.value, str)


def test_finance_personas_map_to_existing_roles_without_new_permissions() -> None:
    catalog = finance_persona_catalog()
    persona_ids = {persona["id"] for persona in catalog}

    assert {
        "owner_admin",
        "controller",
        "cfo",
        "finance_approver",
        "procurement_manager",
        "ap_lead",
        "ar_lead",
        "auditor",
        "executive",
    } <= persona_ids
    assert persona_ids_for_role(UserRole.manager) == [
        "finance_approver",
        "procurement_manager",
        "ap_lead",
        "ar_lead",
    ]
    assert persona_ids_for_role(UserRole.approver) == ["finance_approver"]
    assert persona_ids_for_role(UserRole.auditor) == ["auditor"]
    assert persona_ids_for_role(UserRole.viewer) == ["executive"]
    assert "auditor" not in persona_ids_for_role(UserRole.admin)
    assert all(
        set(persona["mapped_roles"]) <= {role.value for role in UserRole}
        for persona in catalog
    )


def test_admin_outranks_manager() -> None:
    assert ROLE_HIERARCHY[UserRole.admin] > ROLE_HIERARCHY[UserRole.manager]


def test_manager_outranks_member() -> None:
    assert ROLE_HIERARCHY[UserRole.manager] > ROLE_HIERARCHY[UserRole.member]


def test_approver_is_below_manager_for_crud_but_can_approve_manager_threshold() -> None:
    assert ROLE_HIERARCHY[UserRole.approver] < ROLE_HIERARCHY[UserRole.manager]
    assert not role_meets_minimum(UserRole.approver, UserRole.manager)
    assert role_allows_approval(UserRole.approver, UserRole.manager)
    assert not role_allows_approval(UserRole.approver, UserRole.admin)
    assert role_allows_approval(UserRole.manager, UserRole.approver)


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


def _request_with_tenant(path: str = "/") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
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


class _PasswordChangeResult:
    data: ClassVar[list[dict[str, object]]] = [
        {"id": "membership-id", "role": "member", "must_change_password": True}
    ]


class _PasswordChangeQuery(_Query):
    def execute(self):
        return _PasswordChangeResult()


class _PasswordChangeDb:
    def table(self, _name: str):
        return _PasswordChangeQuery()


def test_tenant_dependency_blocks_normal_api_when_password_change_required() -> None:
    with pytest.raises(HTTPException) as exc:
        get_tenant_id(
            _request_with_tenant("/api/v1/clients"),
            CurrentUser(user_id="user-id", email="user@example.com", role="authenticated"),
            _PasswordChangeDb(),  # type: ignore[arg-type]
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "PASSWORD_CHANGE_REQUIRED"


def test_tenant_dependency_allows_password_change_completion_path() -> None:
    tenant_id = get_tenant_id(
        _request_with_tenant("/api/v1/auth/complete-password-change"),
        CurrentUser(user_id="user-id", email="user@example.com", role="authenticated"),
        _PasswordChangeDb(),  # type: ignore[arg-type]
    )

    assert tenant_id == "11111111-1111-1111-1111-111111111111"
