"""API contract for the Timesheet Employee firewall around the main ERP."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.main import app

pytestmark = pytest.mark.unit

TENANT_ID = "11111111-1111-1111-1111-111111111111"
USER_ID = "22222222-2222-4222-8222-222222222222"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _MembershipQuery:
    def __init__(self, db: _MembershipDb, table: str) -> None:
        self._db = db
        self._table = table
        self._update_payload: dict[str, Any] | None = None

    def select(self, _columns: str) -> _MembershipQuery:
        return self

    def eq(self, _key: str, _value: Any) -> _MembershipQuery:
        return self

    def is_(self, _key: str, _value: Any) -> _MembershipQuery:
        return self

    def limit(self, _value: int) -> _MembershipQuery:
        return self

    def update(self, payload: dict[str, Any]) -> _MembershipQuery:
        self._update_payload = dict(payload)
        return self

    def execute(self) -> _Result:
        if self._table == "tenant_user_effective_privileges":
            return _Result([])
        assert self._table == "tenant_users"
        if self._update_payload is not None:
            self._db.updates.append(self._update_payload)
            if "must_change_password" in self._update_payload:
                self._db.must_change_password = bool(
                    self._update_payload["must_change_password"]
                )
        return _Result(
            [
                {
                    "id": "membership-1",
                    "tenant_id": TENANT_ID,
                    "user_id": USER_ID,
                    "role": self._db.role,
                    "must_change_password": self._db.must_change_password,
                }
            ]
        )


class _MembershipDb:
    def __init__(self, role: str, must_change_password: bool = False) -> None:
        self.role = role
        self.must_change_password = must_change_password
        self.updates: list[dict[str, Any]] = []

    def table(self, name: str) -> _MembershipQuery:
        assert name in {"tenant_users", "tenant_user_effective_privileges"}
        return _MembershipQuery(self, name)


class _ErpLeakDb:
    def table(self, name: str) -> None:
        raise AssertionError(f"employee request reached ERP table {name}")


class _PortalQuery:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self._eq_filters: list[tuple[str, Any]] = []
        self._null_filters: list[str] = []

    def select(self, _columns: str) -> _PortalQuery:
        return self

    def eq(self, key: str, value: Any) -> _PortalQuery:
        self._eq_filters.append((key, value))
        return self

    def is_(self, key: str, value: Any) -> _PortalQuery:
        if value == "null":
            self._null_filters.append(key)
        return self

    def limit(self, _value: int) -> _PortalQuery:
        return self

    def order(self, _key: str, desc: bool = False) -> _PortalQuery:
        return self

    def execute(self) -> _Result:
        rows = [
            row
            for row in self._rows
            if all(row.get(key) == value for key, value in self._eq_filters)
            and all(row.get(key) is None for key in self._null_filters)
        ]
        return _Result(rows)


class _PortalDb:
    def __init__(self) -> None:
        self._tables = {
            "employees": [
                {
                    "id": "employee-1",
                    "tenant_id": TENANT_ID,
                    "user_id": USER_ID,
                    "first_name": "Taylor",
                    "last_name": "Consultant",
                    "deleted_at": None,
                }
            ],
            "project_assignments": [],
        }

    def table(self, name: str) -> _PortalQuery:
        assert name in self._tables
        return _PortalQuery(self._tables[name])


class _EmptyQuery:
    def select(self, *_args: Any, **_kwargs: Any) -> _EmptyQuery:
        return self

    def eq(self, *_args: Any, **_kwargs: Any) -> _EmptyQuery:
        return self

    def is_(self, *_args: Any, **_kwargs: Any) -> _EmptyQuery:
        return self

    def order(self, *_args: Any, **_kwargs: Any) -> _EmptyQuery:
        return self

    def limit(self, *_args: Any, **_kwargs: Any) -> _EmptyQuery:
        return self

    def execute(self) -> _Result:
        return _Result([])


class _EmptyErpDb:
    def table(self, _name: str) -> _EmptyQuery:
        return _EmptyQuery()


def _install_overrides(
    role: str = "employee",
    *,
    must_change_password: bool = False,
    rls_db: object | None = None,
) -> _MembershipDb:
    membership_db = _MembershipDb(role, must_change_password)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=USER_ID,
        email="employee@example.com",
        role="authenticated",
    )
    app.dependency_overrides[get_service_role_client] = lambda: membership_db
    app.dependency_overrides[get_user_rls_client] = lambda: rls_db or _ErpLeakDb()
    return membership_db


def test_timesheet_employee_cannot_read_invoices_from_the_main_erp() -> None:
    _install_overrides()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                "/api/v1/invoices",
                headers={"X-Tenant-ID": TENANT_ID},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "TIMESHEET_PORTAL_ONLY"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/bills",
        "/api/v1/reports/balance-sheet",
        "/api/v1/accounting/journal-entries",
        "/api/v1/tenant-users",
        "/api/v1/chat/threads",
    ],
    ids=["bills", "reports", "accounting", "tenant-users", "atlas"],
)
def test_timesheet_employee_cannot_read_main_erp_surfaces(path: str) -> None:
    _install_overrides()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(path, headers={"X-Tenant-ID": TENANT_ID})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "TIMESHEET_PORTAL_ONLY"


def test_role_resolution_cache_cannot_bypass_the_employee_firewall() -> None:
    probe = FastAPI()

    @probe.get("/api/v1/invoices")
    async def cached_role_probe(
        _user: CurrentUser = require_role(UserRole.employee),  # noqa: B008
        _tenant_id: str = Depends(get_tenant_id),
    ) -> dict[str, bool]:
        return {"erp_data": True}

    membership_db = _MembershipDb("employee")
    probe.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=USER_ID,
        email="employee@example.com",
        role="authenticated",
    )
    probe.dependency_overrides[get_service_role_client] = lambda: membership_db

    with TestClient(probe) as client:
        response = client.get(
            "/api/v1/invoices",
            headers={"X-Tenant-ID": TENANT_ID},
        )

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "TIMESHEET_PORTAL_ONLY"


def test_timesheet_employee_can_read_only_their_own_timesheet_portal_data() -> None:
    _install_overrides(rls_db=_PortalDb())
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/timesheet/my-projects",
                headers={"X-Tenant-ID": TENANT_ID},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json() == {"items": [], "total": 0}


def test_timesheet_employee_can_complete_the_forced_password_flow() -> None:
    membership_db = _install_overrides(must_change_password=True)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/complete-password-change",
                headers={"X-Tenant-ID": TENANT_ID},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204, response.text
    assert membership_db.must_change_password is False
    assert membership_db.updates[-1]["must_change_password"] is False


def test_timesheet_employee_can_read_their_effective_portal_permissions() -> None:
    _install_overrides(must_change_password=True)
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/security/me/permissions",
                headers={"X-Tenant-ID": TENANT_ID},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()["legacy_role"] == "employee"
    assert response.json()["role_codes"] == ["timesheet_employee"]


@pytest.mark.parametrize("role", ["owner", "admin"])
def test_owner_and_admin_main_erp_access_is_unaffected(role: str) -> None:
    _install_overrides(role, rls_db=_EmptyErpDb())
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/invoices",
                headers={"X-Tenant-ID": TENANT_ID},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json() == []


def test_public_ping_does_not_require_tenant_membership() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/ping")

    assert response.status_code == 200, response.text
    assert response.json() == {"pong": True}
