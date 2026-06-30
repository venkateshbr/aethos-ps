from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

from app.core.auth import CurrentUser
from app.models.tenant_users import TenantUserInviteRequest, TenantUserUpdateRequest
from app.services.tenant_users_service import TenantUsersService

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-1"
OWNER_ID = "owner-user"
ADMIN_ID = "admin-user"


class _Query:
    def __init__(self, db: _FakeDb, table: str) -> None:
        self.db = db
        self.table = table
        self._eq: list[tuple[str, Any]] = []
        self._is: list[tuple[str, Any]] = []
        self._in: list[tuple[str, list[Any]]] = []
        self._limit: int | None = None
        self._insert: dict[str, Any] | None = None
        self._update: dict[str, Any] | None = None
        self._order_key: str | None = None
        self._order_desc = False
        self._selected_columns: list[str] | None = None

    def select(self, *args: Any, **_kwargs: Any) -> _Query:
        if args and args[0] != "*":
            self._selected_columns = [
                item.strip()
                for item in str(args[0]).replace("\n", " ").split(",")
                if item.strip()
            ]
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq.append((key, value))
        return self

    def is_(self, key: str, value: Any) -> _Query:
        self._is.append((key, value))
        return self

    def in_(self, key: str, values: list[Any]) -> _Query:
        self._in.append((key, values))
        return self

    def limit(self, value: int) -> _Query:
        self._limit = value
        return self

    def order(self, key: str, desc: bool = False) -> _Query:
        self._order_key = key
        self._order_desc = desc
        return self

    def insert(self, payload: dict[str, Any]) -> _Query:
        self._insert = dict(payload)
        return self

    def update(self, payload: dict[str, Any]) -> _Query:
        self._update = dict(payload)
        return self

    def execute(self) -> SimpleNamespace:
        if self._insert is not None:
            row = {
                "id": f"{self.table}-{len(self.db.tables[self.table]) + 1}",
                "created_at": "2026-06-29T00:00:00Z",
                "updated_at": "2026-06-29T00:00:00Z",
                "deleted_at": None,
                **self._insert,
            }
            self.db.tables[self.table].append(row)
            return SimpleNamespace(data=[deepcopy(row)])

        rows = [row for row in self.db.tables[self.table] if self._matches(row)]
        if self._update is not None:
            for row in rows:
                row.update(self._update)
                row["updated_at"] = "2026-06-29T00:01:00Z"
            return SimpleNamespace(data=deepcopy(rows))

        if self._order_key:
            rows.sort(key=lambda row: str(row.get(self._order_key) or ""), reverse=self._order_desc)
        if self._limit is not None:
            rows = rows[: self._limit]
        if self._selected_columns is not None:
            rows = [
                {column: row.get(column) for column in self._selected_columns}
                for row in rows
            ]
        return SimpleNamespace(data=deepcopy(rows))

    def _matches(self, row: dict[str, Any]) -> bool:
        for key, value in self._eq:
            if row.get(key) != value:
                return False
        for key, value in self._is:
            if value == "null" and row.get(key) is not None:
                return False
            if value != "null" and row.get(key) is not value:
                return False
        for key, values in self._in:
            if row.get(key) not in values:
                return False
        return True


class _FakeAuthAdmin:
    def __init__(self) -> None:
        self.created_users: list[dict[str, Any]] = []
        self.updated_users: list[tuple[str, dict[str, Any]]] = []

    def create_user(self, payload: dict[str, Any]) -> SimpleNamespace:
        self.created_users.append(payload)
        return SimpleNamespace(user=SimpleNamespace(id=f"auth-{len(self.created_users)}"))

    def generate_link(self, _payload: dict[str, Any]) -> SimpleNamespace:
        return SimpleNamespace(properties=SimpleNamespace(action_link="https://set-password.test/link"))

    def update_user_by_id(self, user_id: str, payload: dict[str, Any]) -> None:
        self.updated_users.append((user_id, payload))


class _FakeDb:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.tables = {
            "tenant_users": rows,
            "tenant_user_audit_events": [],
            "tenant_user_role_audit_events": [],
            "tenant_user_roles": [],
            "security_roles": _security_roles(),
            "tenant_user_effective_privileges": _effective_privileges(rows),
        }
        self.auth = SimpleNamespace(admin=_FakeAuthAdmin())

    def table(self, name: str) -> _Query:
        assert name in self.tables
        return _Query(self, name)


def _tenant_user(**overrides: Any) -> dict[str, Any]:
    row = {
        "id": "tu-owner",
        "tenant_id": TENANT_ID,
        "user_id": OWNER_ID,
        "email": "owner@aethos-qa.dev",
        "display_name": "Owner User",
        "role": "owner",
        "invited_at": None,
        "joined_at": "2026-06-29T00:00:00Z",
        "created_at": "2026-06-29T00:00:00Z",
        "updated_at": "2026-06-29T00:00:00Z",
        "deleted_at": None,
        "deactivated_at": None,
        "must_change_password": False,
    }
    row.update(overrides)
    return row


@pytest.mark.asyncio
async def test_owner_can_invite_manager_user() -> None:
    db = _FakeDb([_tenant_user()])
    svc = TenantUsersService(db, TENANT_ID)  # type: ignore[arg-type]

    response = await svc.invite_user(
        TenantUserInviteRequest(email="manager@aethos-qa.dev", role="manager"),
        actor=CurrentUser(user_id=OWNER_ID, email="owner@aethos-qa.dev", role="owner"),
    )

    assert response.email == "manager@aethos-qa.dev"
    assert response.role == "manager"
    assert response.role_codes == ["finance_ops_manager"]
    assert response.must_change_password is True
    assert response.temp_password
    assert response.set_password_url == "https://set-password.test/link"
    assert db.auth.admin.created_users[0]["app_metadata"]["role"] == "manager"
    assert db.auth.admin.created_users[0]["app_metadata"]["role_codes"] == ["finance_ops_manager"]
    assert db.auth.admin.created_users[0]["app_metadata"]["must_change_password"] is True
    assert db.tables["tenant_user_audit_events"][0]["action"] == "invited"


@pytest.mark.asyncio
async def test_list_users_includes_initial_password_change_status() -> None:
    db = _FakeDb(
        [
            _tenant_user(),
            _tenant_user(
                id="tu-initial-password",
                user_id="initial-password-user",
                email="initial-password@aethos-qa.dev",
                role="member",
                must_change_password=True,
            ),
        ]
    )
    svc = TenantUsersService(db, TENANT_ID)  # type: ignore[arg-type]

    response = await svc.list_users()

    by_email = {item.email: item for item in response.items}
    assert by_email["initial-password@aethos-qa.dev"].must_change_password is True


@pytest.mark.asyncio
async def test_admin_can_invite_approver_and_auditor_users() -> None:
    db = _FakeDb(
        [
            _tenant_user(),
            _tenant_user(id="tu-admin", user_id=ADMIN_ID, role="admin", email="admin@aethos-qa.dev"),
        ]
    )
    svc = TenantUsersService(db, TENANT_ID)  # type: ignore[arg-type]

    approver = await svc.invite_user(
        TenantUserInviteRequest(email="approver@aethos-qa.dev", role="approver"),
        actor=CurrentUser(user_id=ADMIN_ID, email="admin@aethos-qa.dev", role="admin"),
    )
    auditor = await svc.invite_user(
        TenantUserInviteRequest(email="auditor@aethos-qa.dev", role="auditor"),
        actor=CurrentUser(user_id=ADMIN_ID, email="admin@aethos-qa.dev", role="admin"),
    )

    assert approver.role == "approver"
    assert auditor.role == "auditor"
    assert db.auth.admin.created_users[0]["app_metadata"]["role"] == "approver"
    assert db.auth.admin.created_users[1]["app_metadata"]["role"] == "auditor"


@pytest.mark.asyncio
async def test_admin_can_invite_admin_user_but_not_owner() -> None:
    db = _FakeDb(
        [
            _tenant_user(),
            _tenant_user(id="tu-admin", user_id=ADMIN_ID, role="admin", email="admin@aethos-qa.dev"),
        ]
    )
    svc = TenantUsersService(db, TENANT_ID)  # type: ignore[arg-type]

    response = await svc.invite_user(
        TenantUserInviteRequest(email="next-admin@aethos-qa.dev", role="admin"),
        actor=CurrentUser(user_id=ADMIN_ID, email="admin@aethos-qa.dev", role="admin"),
    )
    assert response.role == "admin"

    with pytest.raises(HTTPException) as exc:
        await svc.invite_user(
            TenantUserInviteRequest(email="owner-2@aethos-qa.dev", role="owner"),
            actor=CurrentUser(user_id=ADMIN_ID, email="admin@aethos-qa.dev", role="admin"),
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_user_cannot_deactivate_self() -> None:
    db = _FakeDb([_tenant_user()])
    svc = TenantUsersService(db, TENANT_ID)  # type: ignore[arg-type]

    with pytest.raises(HTTPException) as exc:
        await svc.deactivate_user(
            "tu-owner",
            actor=CurrentUser(user_id=OWNER_ID, email="owner@aethos-qa.dev", role="owner"),
        )

    assert exc.value.status_code == 403
    assert db.tables["tenant_user_audit_events"] == []


@pytest.mark.asyncio
async def test_owner_role_change_updates_auth_metadata_and_audit() -> None:
    db = _FakeDb(
        [
            _tenant_user(),
            _tenant_user(id="tu-member", user_id="member-user", role="member", email="member@aethos-qa.dev"),
        ]
    )
    svc = TenantUsersService(db, TENANT_ID)  # type: ignore[arg-type]

    response = await svc.update_user(
        "tu-member",
        TenantUserUpdateRequest(role="manager"),
        actor=CurrentUser(user_id=OWNER_ID, email="owner@aethos-qa.dev", role="owner"),
    )

    assert response.role == "manager"
    assert db.auth.admin.updated_users == [
        (
            "member-user",
            {
                "app_metadata": {
                    "role": "manager",
                    "role_codes": ["finance_ops_manager"],
                    "tenant_id": TENANT_ID,
                }
            },
        )
    ]
    assert db.tables["tenant_user_audit_events"][0]["action"] == "role_changed"
    assert db.tables["tenant_user_audit_events"][0]["previous_role"] == "member"
    assert db.tables["tenant_user_audit_events"][0]["new_role"] == "manager"


def _security_roles() -> list[dict[str, Any]]:
    rows = []
    for code, label, legacy_role in [
        ("tenant_owner", "Tenant Owner", "owner"),
        ("tenant_admin", "Tenant Admin", "admin"),
        ("finance_ops_manager", "Finance Ops Manager", "manager"),
        ("finance_approver", "Finance Approver", "approver"),
        ("finance_operator", "Finance Operator", "member"),
        ("auditor", "Auditor", "auditor"),
        ("executive_viewer", "Executive Viewer", "viewer"),
    ]:
        rows.append(
            {
                "id": f"role-{code}",
                "tenant_id": None,
                "code": code,
                "label": label,
                "description": "",
                "legacy_role": legacy_role,
                "is_system": True,
                "is_assignable": True,
                "rank": 1,
                "deleted_at": None,
            }
        )
    return rows


def _effective_privileges(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        if row.get("role") not in {"owner", "admin"}:
            continue
        role_code = "tenant_owner" if row["role"] == "owner" else "tenant_admin"
        for privilege in ("tenant.users.manage", "security.roles.manage"):
            output.append(
                {
                    "tenant_id": row["tenant_id"],
                    "user_id": row["user_id"],
                    "tenant_user_id": row["id"],
                    "role_code": role_code,
                    "role_label": role_code.replace("_", " ").title(),
                    "legacy_role": row["role"],
                    "privilege_code": privilege,
                    "privilege_label": privilege,
                    "privilege_category": "Security",
                }
            )
    return output
