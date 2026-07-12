"""Contracts for real-stack scenario membership security assignments."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from tests.fixtures import scenarios
from tests.fixtures.scenarios import SeedUser, _ensure_membership

pytestmark = pytest.mark.unit


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _FixtureDb, table: str) -> None:
        self._db = db
        self._table = table
        self._filters: list[tuple[str, Any]] = []
        self._limit: int | None = None
        self._insert_payload: dict[str, Any] | None = None

    def select(self, _columns: str) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._filters.append((key, value))
        return self

    def is_(self, key: str, value: str) -> _Query:
        if value == "null":
            self._filters.append((key, None))
        return self

    def limit(self, value: int) -> _Query:
        self._limit = value
        return self

    def insert(self, payload: dict[str, Any]) -> _Query:
        self._insert_payload = dict(payload)
        return self

    def execute(self) -> _Result:
        if self._insert_payload is not None:
            row = dict(self._insert_payload)
            row.setdefault("id", f"{self._table}-{len(self._db.tables[self._table]) + 1}")
            row.setdefault("deleted_at", None)
            self._db.tables[self._table].append(row)
            return _Result([deepcopy(row)])

        rows = [
            row
            for row in self._db.tables[self._table]
            if all(row.get(key) == value for key, value in self._filters)
        ]
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Result(deepcopy(rows))


class _FixtureDb:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "tenant_users": [],
            "security_roles": [
                {
                    "id": "role-owner",
                    "tenant_id": None,
                    "code": "tenant_owner",
                    "deleted_at": None,
                },
                {
                    "id": "role-manager",
                    "tenant_id": None,
                    "code": "finance_ops_manager",
                    "deleted_at": None,
                },
                {
                    "id": "role-viewer",
                    "tenant_id": None,
                    "code": "executive_viewer",
                    "deleted_at": None,
                },
            ],
            "tenant_user_roles": [],
        }

    def table(self, name: str) -> _Query:
        return _Query(self, name)


def test_membership_receives_one_canonical_catalog_role_on_reseed() -> None:
    db = _FixtureDb()
    user = SeedUser(user_id="user-owner", email="owner@example.com", role="owner")

    _ensure_membership(db, tenant_id="tenant-1", user=user)  # type: ignore[arg-type]
    _ensure_membership(db, tenant_id="tenant-1", user=user)  # type: ignore[arg-type]

    memberships = db.tables["tenant_users"]
    assignments = db.tables["tenant_user_roles"]
    assert len(memberships) == 1
    assert assignments == [
        {
            "id": "tenant_user_roles-1",
            "tenant_id": "tenant-1",
            "tenant_user_id": memberships[0]["id"],
            "security_role_id": "role-owner",
            "deleted_at": None,
        }
    ]


def test_membership_rejects_an_unexpected_active_catalog_role() -> None:
    db = _FixtureDb()
    db.tables["tenant_users"].append(
        {
            "id": "membership-owner",
            "tenant_id": "tenant-1",
            "user_id": "user-owner",
            "role": "owner",
            "deleted_at": None,
        }
    )
    db.tables["tenant_user_roles"].append(
        {
            "id": "assignment-viewer",
            "tenant_id": "tenant-1",
            "tenant_user_id": "membership-owner",
            "security_role_id": "role-viewer",
            "deleted_at": None,
        }
    )
    user = SeedUser(user_id="user-owner", email="owner@example.com", role="owner")

    with pytest.raises(RuntimeError, match="unexpected active security role"):
        _ensure_membership(db, tenant_id="tenant-1", user=user)  # type: ignore[arg-type]


def test_scenario_user_ids_are_stable_and_role_specific() -> None:
    owner_id = scenarios._scenario_user_id("tenant-a-owner")

    assert scenarios._scenario_user_id("tenant-a-owner") == owner_id
    assert scenarios._scenario_user_id("tenant-a-manager") != owner_id


@pytest.mark.parametrize(
    ("legacy_role", "expected_security_role_id"),
    [
        ("owner", "role-owner"),
        ("manager", "role-manager"),
        ("viewer", "role-viewer"),
    ],
)
def test_real_stack_roles_use_the_canonical_catalog_mapping(
    legacy_role: str,
    expected_security_role_id: str,
) -> None:
    db = _FixtureDb()
    user = SeedUser(
        user_id=f"user-{legacy_role}",
        email=f"{legacy_role}@example.com",
        role=legacy_role,
    )

    _ensure_membership(db, tenant_id="tenant-1", user=user)  # type: ignore[arg-type]

    assert db.tables["tenant_user_roles"][0]["security_role_id"] == (
        expected_security_role_id
    )


def test_membership_fails_when_migration_0096_roles_are_missing() -> None:
    db = _FixtureDb()
    db.tables["security_roles"] = []
    user = SeedUser(user_id="user-owner", email="owner@example.com", role="owner")

    with pytest.raises(RuntimeError, match="apply migration 0096"):
        _ensure_membership(db, tenant_id="tenant-1", user=user)  # type: ignore[arg-type]
