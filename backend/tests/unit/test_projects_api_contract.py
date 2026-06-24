"""Projects API contract tests for RLS-backed reads and service-role writes."""

from __future__ import annotations

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
    def __init__(self, data: Any) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _FakeDb, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, Any]] = []
        self._in_filters: list[tuple[str, list[Any]]] = []
        self._null_filters: list[str] = []
        self._order_key: str | None = None
        self._order_desc = False
        self._range: tuple[int, int] | None = None
        self._limit: int | None = None
        self._single = False
        self._insert_payload: dict[str, Any] | None = None
        self._update_payload: dict[str, Any] | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def in_(self, key: str, values: list[Any]) -> _Query:
        self._in_filters.append((key, values))
        return self

    def is_(self, key: str, value: Any) -> _Query:
        if value == "null":
            self._null_filters.append(key)
        return self

    def order(self, key: str, *, desc: bool = False) -> _Query:
        self._order_key = key
        self._order_desc = desc
        return self

    def range(self, start: int, end: int) -> _Query:
        self._range = (start, end)
        return self

    def limit(self, limit: int) -> _Query:
        self._limit = limit
        return self

    def single(self) -> _Query:
        self._single = True
        return self

    def insert(self, payload: dict[str, Any]) -> _Query:
        self._insert_payload = dict(payload)
        return self

    def update(self, payload: dict[str, Any]) -> _Query:
        self._update_payload = dict(payload)
        return self

    def execute(self) -> _Result:
        if self._insert_payload is not None:
            if self.table == "project_phases":
                row = {
                    "id": "phase-created",
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "updated_at": "2026-06-22T00:00:00+00:00",
                    "deleted_at": None,
                    **self._insert_payload,
                }
            else:
                row = {
                    "id": "project-created",
                    "code": "PRJ-0003",
                    "budget": None,
                    "budget_hours": None,
                    "status": "planning",
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "deleted_at": None,
                    **self._insert_payload,
                }
            self.db.tables[self.table].append(row)
            return _Result([row])

        if self._update_payload is not None:
            rows = self._filtered_rows()
            updated_rows: list[dict[str, Any]] = []
            for row in rows:
                row.update(self._update_payload)
                row["updated_at"] = "2026-06-23T00:00:00+00:00"
                updated_rows.append(row)
            return _Result(updated_rows)

        rows = self._filtered_rows()
        if self._order_key is not None:
            rows.sort(
                key=lambda row: str(row.get(self._order_key) or ""),
                reverse=self._order_desc,
            )
        if self._range is not None:
            start, end = self._range
            rows = rows[start : end + 1]
        if self._limit is not None:
            rows = rows[: self._limit]
        if self._single:
            return _Result(rows[0] if rows else None)
        return _Result(rows)

    def _filtered_rows(self) -> list[dict[str, Any]]:
        rows = list(self.db.tables[self.table])
        for key, value in self._eq_filters:
            rows = [row for row in rows if row.get(key) == value]
        for key, values in self._in_filters:
            rows = [row for row in rows if row.get(key) in values]
        for key in self._null_filters:
            rows = [row for row in rows if row.get(key) is None]
        return rows


class _FakeDb:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "engagements": [
                {
                    "id": "eng-1",
                    "tenant_id": TENANT_ID,
                    "currency": "USD",
                    "deleted_at": None,
                }
            ],
            "projects": [
                {
                    "id": "project-alpha",
                    "tenant_id": TENANT_ID,
                    "engagement_id": "eng-1",
                    "code": "PRJ-0001",
                    "name": "Alpha",
                    "currency": "USD",
                    "budget": "50000.00",
                    "budget_hours": "300.00",
                    "status": "active",
                    "start_date": "2026-06-01",
                    "end_date": "2026-07-31",
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "deleted_at": None,
                },
                {
                    "id": "project-beta",
                    "tenant_id": TENANT_ID,
                    "engagement_id": "eng-2",
                    "code": "PRJ-0002",
                    "name": "Beta",
                    "currency": "USD",
                    "budget": "30000.00",
                    "budget_hours": None,
                    "status": "planning",
                    "start_date": None,
                    "end_date": None,
                    "created_at": "2026-06-21T00:00:00+00:00",
                    "deleted_at": None,
                },
                {
                    "id": "project-other-tenant",
                    "tenant_id": "tenant-other",
                    "engagement_id": "eng-other",
                    "code": "PRJ-9999",
                    "name": "Other Tenant",
                    "currency": "USD",
                    "budget": "1.00",
                    "budget_hours": None,
                    "status": "active",
                    "start_date": None,
                    "end_date": None,
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "deleted_at": None,
                },
            ],
            "project_phases": [
                {
                    "id": "phase-1",
                    "tenant_id": TENANT_ID,
                    "project_id": "project-alpha",
                    "name": "Discovery",
                    "description": None,
                    "status": "active",
                    "start_date": "2026-06-01",
                    "end_date": "2026-06-15",
                    "budget": "10000.00",
                    "order_index": 0,
                    "deliverable_name": "Discovery brief",
                    "deliverable_acceptance_criteria": "Signed off by sponsor",
                    "percent_complete": "40",
                    "revenue_recognition_amount": "12000.00",
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "updated_at": "2026-06-22T00:00:00+00:00",
                    "deleted_at": None,
                }
            ],
            "project_assignments": [
                {
                    "id": "assignment-1",
                    "tenant_id": TENANT_ID,
                    "project_id": "project-alpha",
                    "employee_id": "employee-1",
                    "role": "Consultant",
                    "override_rate": "200.00",
                    "start_date": "2026-06-01",
                    "end_date": None,
                    "created_at": "2026-06-22T00:00:00+00:00",
                }
            ],
            "employees": [
                {
                    "id": "employee-1",
                    "tenant_id": TENANT_ID,
                    "first_name": "Taylor",
                    "last_name": "Consultant",
                    "email": "taylor@example.com",
                    "deleted_at": None,
                }
            ],
        }

    def table(self, name: str) -> _Query:
        return _Query(self, name)


class _ForbiddenDb:
    def table(self, name: str) -> None:
        raise AssertionError(f"wrong dependency attempted to access {name}")


@pytest.fixture
def fake_db() -> _FakeDb:
    return _FakeDb()


@pytest.fixture
def client(fake_db: _FakeDb) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="owner@example.com",
        role="owner",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_project_read_routes_use_rls_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    list_response = client.get("/api/v1/projects?engagement_id=eng-1&limit=10")
    detail_response = client.get("/api/v1/projects/project-alpha")
    assignments_response = client.get("/api/v1/projects/project-alpha/assignments")
    phases_response = client.get("/api/v1/projects/project-alpha/phases")

    assert list_response.status_code == 200, list_response.text
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == "project-alpha"
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["name"] == "Alpha"
    assert assignments_response.status_code == 200, assignments_response.text
    assert assignments_response.json()["items"][0]["id"] == "assignment-1"
    assert assignments_response.json()["items"][0]["employee_name"] == "Taylor Consultant"
    assert phases_response.status_code == 200, phases_response.text
    assert phases_response.json()[0]["deliverable_name"] == "Discovery brief"
    assert phases_response.json()[0]["percent_complete"] == "40"
    assert phases_response.json()[0]["revenue_recognition_amount"] == "12000.00"


def test_project_create_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    response = client.post(
        "/api/v1/projects",
        json={
            "engagement_id": "eng-1",
            "name": "Created Project",
            "currency": "USD",
            "budget": "12000.00",
            "budget_hours": "80",
            "status": "active",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["id"] == "project-created"
    assert response.json()["tenant_id"] == TENANT_ID
    assert response.json()["engagement_id"] == "eng-1"
    assert response.json()["budget_hours"] == "80"
    assert response.json()["status"] == "active"


def test_project_phase_create_and_update_use_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    create_response = client.post(
        "/api/v1/projects/project-alpha/phases",
        json={
            "name": "Build",
            "status": "planning",
            "end_date": "2026-07-15",
            "budget": "15000.00",
            "revenue_recognition_amount": "20000.00",
            "deliverable_name": "Working process prototype",
            "deliverable_acceptance_criteria": "Sponsor signs UAT checklist",
            "percent_complete": "10",
            "order_index": 1,
        },
    )
    update_response = client.patch(
        "/api/v1/projects/project-alpha/phases/phase-created",
        json={
            "status": "active",
            "revenue_recognition_amount": "22000.00",
            "percent_complete": "35",
        },
    )

    assert create_response.status_code == 201, create_response.text
    assert create_response.json()["id"] == "phase-created"
    assert create_response.json()["deliverable_name"] == "Working process prototype"
    assert create_response.json()["revenue_recognition_amount"] == "20000.00"
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["status"] == "active"
    assert update_response.json()["percent_complete"] == "35"
    assert update_response.json()["revenue_recognition_amount"] == "22000.00"
