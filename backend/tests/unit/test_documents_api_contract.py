"""Documents API contract tests for RLS-backed metadata reads."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.tenant import get_tenant_id
from app.main import app

pytestmark = pytest.mark.unit

TENANT_ID = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT_ID = "22222222-2222-2222-2222-222222222222"
DOCUMENT_ID = "33333333-3333-4333-8333-333333333333"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _FakeDb, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, Any]] = []
        self._order_key: str | None = None
        self._order_desc = False
        self._limit: int | None = None

    def select(self, _columns: str = "*", **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def order(self, key: str, desc: bool = False) -> _Query:
        self._order_key = key
        self._order_desc = desc
        return self

    def limit(self, limit: int) -> _Query:
        self._limit = limit
        return self

    def execute(self) -> _Result:
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
        return all(row.get(key) == value for key, value in self._eq_filters)


class _FakeDb:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "documents": [
                {
                    "id": DOCUMENT_ID,
                    "tenant_id": TENANT_ID,
                    "original_filename": "acme-invoice.pdf",
                    "mime_type": "application/pdf",
                    "storage_path": f"{TENANT_ID}/2026/06/{DOCUMENT_ID}.pdf",
                    "document_type": "vendor_invoice",
                    "status": "extracted",
                    "created_at": "2026-06-22T00:00:00+00:00",
                },
                {
                    "id": "44444444-4444-4444-8444-444444444444",
                    "tenant_id": OTHER_TENANT_ID,
                    "original_filename": "foreign.pdf",
                    "mime_type": "application/pdf",
                    "storage_path": f"{OTHER_TENANT_ID}/2026/06/foreign.pdf",
                    "document_type": "vendor_invoice",
                    "status": "uploaded",
                    "created_at": "2026-06-23T00:00:00+00:00",
                },
            ]
        }

    def table(self, name: str) -> _Query:
        assert name in self.tables
        return _Query(self, name)


class _ForbiddenDb:
    def table(self, name: str) -> None:
        raise AssertionError(f"wrong dependency attempted to access {name}")


class _SignedUrlBucket:
    def __init__(self, db: _StorageDb) -> None:
        self.db = db

    def create_signed_url(self, path: str, expires_in: int) -> dict[str, str]:
        self.db.signed_url_requests.append((path, expires_in))
        return {"signedURL": f"https://storage.example.test/{path}?sig=test"}


class _Storage:
    def __init__(self, db: _StorageDb) -> None:
        self.db = db

    def from_(self, bucket: str) -> _SignedUrlBucket:
        self.db.buckets.append(bucket)
        return _SignedUrlBucket(self.db)


class _StorageDb:
    def __init__(self) -> None:
        self.buckets: list[str] = []
        self.signed_url_requests: list[tuple[str, int]] = []
        self.storage = _Storage(self)

    def table(self, name: str) -> None:
        raise AssertionError(f"storage dependency attempted to access {name}")


def test_document_list_uses_rls_client() -> None:
    fake_db = _FakeDb()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="viewer@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/documents")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json() == [
        {
            "id": DOCUMENT_ID,
            "filename": "acme-invoice.pdf",
            "mime_type": "application/pdf",
            "document_type": "vendor_invoice",
            "status": "extracted",
            "created_at": "2026-06-22T00:00:00+00:00",
        }
    ]


def test_document_url_authorizes_with_rls_and_uses_service_role_for_storage() -> None:
    fake_db = _FakeDb()
    storage_db = _StorageDb()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="viewer@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: storage_db

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/documents/{DOCUMENT_ID}/url?expires_in=600")
    finally:
        app.dependency_overrides.clear()

    storage_path = f"{TENANT_ID}/2026/06/{DOCUMENT_ID}.pdf"
    assert response.status_code == 200, response.text
    assert response.json() == {
        "document_id": DOCUMENT_ID,
        "url": f"https://storage.example.test/{storage_path}?sig=test",
        "original_filename": "acme-invoice.pdf",
        "mime_type": "application/pdf",
        "expires_in": 600,
    }
    assert storage_db.buckets == ["documents"]
    assert storage_db.signed_url_requests == [(storage_path, 600)]
