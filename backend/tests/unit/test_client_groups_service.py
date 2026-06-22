"""Unit tests for tenant-scoped client groups."""

from __future__ import annotations

from typing import Any

import pytest

from app.models.client_groups import ClientGroupCreate, ClientGroupMemberCreate
from app.services.client_groups_service import ClientGroupsService

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-test-001"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _FakeDb, table: str) -> None:
        self.db = db
        self.table = table
        self.rows = list(db.tables[table])
        self._select = ""
        self._insert_payload: dict[str, Any] | None = None
        self._update_payload: dict[str, Any] | None = None

    def select(self, columns: str) -> _Query:
        self._select = columns
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self.rows = [row for row in self.rows if row.get(key) == value]
        return self

    def in_(self, key: str, values: list[Any]) -> _Query:
        value_set = set(values)
        self.rows = [row for row in self.rows if row.get(key) in value_set]
        return self

    def is_(self, key: str, value: Any) -> _Query:
        if value == "null":
            self.rows = [row for row in self.rows if row.get(key) is None]
        return self

    def order(self, key: str) -> _Query:
        self.rows = sorted(self.rows, key=lambda row: row.get(key) or "")
        return self

    def insert(self, payload: dict[str, Any]) -> _Query:
        self._insert_payload = payload
        return self

    def update(self, payload: dict[str, Any]) -> _Query:
        self._update_payload = payload
        return self

    def execute(self) -> _Result:
        if self._insert_payload is not None:
            row = dict(self._insert_payload)
            row.setdefault("id", self.db.next_id(self.table))
            row.setdefault("created_at", "2026-06-22T00:00:00+00:00")
            row.setdefault("updated_at", "2026-06-22T00:00:00+00:00")
            row.setdefault("deleted_at", None)
            self.db.tables[self.table].append(row)
            return _Result([self._embed(row)])

        if self._update_payload is not None:
            updated: list[dict[str, Any]] = []
            for row in self.rows:
                row.update(self._update_payload)
                updated.append(row)
            return _Result([self._embed(row) for row in updated])

        return _Result([self._embed(row) for row in self.rows])

    def _embed(self, row: dict[str, Any]) -> dict[str, Any]:
        result = dict(row)
        if self.table == "client_group_members" and "clients!client_id" in self._select:
            result["clients"] = self.db.client_by_id.get(str(row["client_id"]))
        return result


class _FakeDb:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "clients": [
                {
                    "id": "client-acme",
                    "tenant_id": TENANT_ID,
                    "name": "Acme Corp",
                    "kind": "customer",
                    "deleted_at": None,
                },
                {
                    "id": "client-bravo",
                    "tenant_id": TENANT_ID,
                    "name": "Bravo Holdings",
                    "kind": "both",
                    "deleted_at": None,
                },
            ],
            "client_groups": [],
            "client_group_members": [],
        }
        self.client_by_id = {
            str(row["id"]): {"id": row["id"], "name": row["name"], "kind": row["kind"]}
            for row in self.tables["clients"]
        }
        self._sequences = {"client_groups": 1, "client_group_members": 1}

    def next_id(self, table: str) -> str:
        value = self._sequences[table]
        self._sequences[table] = value + 1
        prefix = "group" if table == "client_groups" else "member"
        return f"{prefix}-{value}"

    def table(self, name: str) -> _Query:
        return _Query(self, name)


def test_create_group_adds_primary_member_and_normalizes_currency() -> None:
    db = _FakeDb()
    svc = ClientGroupsService(db, TENANT_ID)

    result = svc.create_group(
        ClientGroupCreate(
            name="Acme Family Office",
            group_type="family_office",
            primary_client_id="client-acme",
            billing_client_id="client-acme",
            currency="usd",
        )
    )

    assert result.name == "Acme Family Office"
    assert result.currency == "USD"
    assert result.primary_client_id == "client-acme"
    assert result.billing_client_id == "client-acme"
    assert result.member_count == 1
    assert result.members[0].client_name == "Acme Corp"
    assert result.members[0].relationship_role == "parent"
    assert result.members[0].is_primary is True

    group_row = db.tables["client_groups"][0]
    member_row = db.tables["client_group_members"][0]
    assert group_row["tenant_id"] == TENANT_ID
    assert member_row["tenant_id"] == TENANT_ID
    assert member_row["group_id"] == result.id


def test_add_member_updates_primary_and_billing_entity_links() -> None:
    db = _FakeDb()
    db.tables["client_groups"].append(
        {
            "id": "group-1",
            "tenant_id": TENANT_ID,
            "name": "Acme Group",
            "group_type": "client_relationship",
            "primary_client_id": "client-acme",
            "billing_client_id": "client-acme",
            "currency": "USD",
            "status": "active",
            "created_at": "2026-06-22T00:00:00+00:00",
            "updated_at": "2026-06-22T00:00:00+00:00",
            "deleted_at": None,
        }
    )
    db.tables["client_group_members"].append(
        {
            "id": "member-1",
            "tenant_id": TENANT_ID,
            "group_id": "group-1",
            "client_id": "client-acme",
            "relationship_role": "parent",
            "is_primary": True,
            "start_date": None,
            "end_date": None,
            "created_at": "2026-06-22T00:00:00+00:00",
            "updated_at": "2026-06-22T00:00:00+00:00",
            "deleted_at": None,
        }
    )
    svc = ClientGroupsService(db, TENANT_ID)

    result = svc.add_member(
        "group-1",
        ClientGroupMemberCreate(
            client_id="client-bravo",
            relationship_role="billing_entity",
            is_primary=True,
        ),
    )

    assert result.client_name == "Bravo Holdings"
    assert result.relationship_role == "billing_entity"
    assert result.is_primary is True

    old_member = next(row for row in db.tables["client_group_members"] if row["id"] == "member-1")
    group = db.tables["client_groups"][0]
    assert old_member["is_primary"] is False
    assert group["primary_client_id"] == "client-bravo"
    assert group["billing_client_id"] == "client-bravo"
