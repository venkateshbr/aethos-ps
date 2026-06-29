"""Documents API contract tests for RLS-backed metadata reads."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from unittest.mock import AsyncMock, patch

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
        self._insert_row: dict[str, Any] | None = None

    def select(self, _columns: str = "*", **_kwargs: Any) -> _Query:
        return self

    def insert(self, row: dict[str, Any]) -> _Query:
        self._insert_row = deepcopy(row)
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
        if self._insert_row is not None:
            self.db.tables[self.table].append(deepcopy(self._insert_row))
            return _Result([deepcopy(self._insert_row)])

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
                    "file_size_bytes": 1234,
                    "sha256": "a" * 64,
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
                    "file_size_bytes": 999,
                    "sha256": "b" * 64,
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


class _UploadBucket:
    def __init__(self, db: _UploadDb) -> None:
        self.db = db

    def upload(self, path: str, file: bytes, file_options: dict[str, Any]) -> None:
        self.db.uploads.append(
            {
                "path": path,
                "file": file,
                "file_options": deepcopy(file_options),
            }
        )


class _UploadStorage:
    def __init__(self, db: _UploadDb) -> None:
        self.db = db

    def from_(self, bucket: str) -> _UploadBucket:
        self.db.buckets.append(bucket)
        return _UploadBucket(self.db)


class _UploadDb(_FakeDb):
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        super().__init__()
        self.tables["documents"] = rows or []
        self.buckets: list[str] = []
        self.uploads: list[dict[str, Any]] = []
        self.storage = _UploadStorage(self)


def _current_user() -> CurrentUser:
    return CurrentUser(
        user_id="user-1",
        email="viewer@example.com",
        role="viewer",
    )


def _document_row(*, status: str = "uploaded") -> dict[str, Any]:
    return {
        "id": DOCUMENT_ID,
        "tenant_id": TENANT_ID,
        "original_filename": "acme-invoice.txt",
        "mime_type": "text/plain",
        "storage_path": f"{TENANT_ID}/2026/06/{DOCUMENT_ID}.txt",
        "file_size_bytes": 1234,
        "sha256": "a" * 64,
        "document_type": "vendor_invoice",
        "status": status,
        "created_at": "2026-06-22T00:00:00+00:00",
    }


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


def test_document_detail_uses_rls_client_and_returns_status() -> None:
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
            response = client.get(f"/api/v1/documents/{DOCUMENT_ID}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json() == {
        "id": DOCUMENT_ID,
        "tenant_id": TENANT_ID,
        "original_filename": "acme-invoice.pdf",
        "document_type": "vendor_invoice",
        "storage_path": f"{TENANT_ID}/2026/06/{DOCUMENT_ID}.pdf",
        "mime_type": "application/pdf",
        "file_size_bytes": 1234,
        "sha256": "a" * 64,
        "status": "extracted",
        "created_at": "2026-06-22T00:00:00+00:00",
    }


def test_document_detail_cross_tenant_yields_404() -> None:
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
            response = client.get("/api/v1/documents/44444444-4444-4444-8444-444444444444")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404, response.text


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


def test_upload_process_false_stores_document_without_dispatching_extraction() -> None:
    upload_db = _UploadDb()
    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_service_role_client] = lambda: upload_db
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()

    try:
        with patch(
            "app.api.v1.endpoints.documents._dispatch_extraction",
            new_callable=AsyncMock,
        ) as dispatch:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/documents/upload",
                    files={"file": ("acme-invoice.txt", b"Vendor invoice", "text/plain")},
                    data={"process": "false"},
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "uploaded"
    assert body["original_filename"] == "acme-invoice.txt"
    assert body["tenant_id"] == TENANT_ID
    assert upload_db.buckets == ["documents"]
    assert upload_db.uploads[0]["file"] == b"Vendor invoice"
    assert upload_db.tables["documents"][0]["status"] == "uploaded"
    dispatch.assert_not_awaited()


def test_upload_defaults_to_dispatching_extraction() -> None:
    upload_db = _UploadDb()
    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_service_role_client] = lambda: upload_db
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()

    async def mark_extracted(*, document_id: str, tenant_id: str) -> None:
        for row in upload_db.tables["documents"]:
            if row["id"] == document_id and row["tenant_id"] == tenant_id:
                row["status"] = "extracted"

    try:
        with patch(
            "app.api.v1.endpoints.documents._dispatch_extraction",
            new_callable=AsyncMock,
            side_effect=mark_extracted,
        ) as dispatch:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/documents/upload",
                    files={"file": ("acme-invoice.txt", b"Vendor invoice", "text/plain")},
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "extracted"
    dispatch.assert_awaited_once_with(document_id=body["id"], tenant_id=TENANT_ID)


def test_extract_document_endpoint_dispatches_uploaded_document() -> None:
    upload_db = _UploadDb(rows=[_document_row(status="uploaded")])
    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_service_role_client] = lambda: upload_db
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()

    async def mark_extracted(*, document_id: str, tenant_id: str) -> None:
        for row in upload_db.tables["documents"]:
            if row["id"] == document_id and row["tenant_id"] == tenant_id:
                row["status"] = "extracted"

    try:
        with patch(
            "app.api.v1.endpoints.documents._dispatch_extraction",
            new_callable=AsyncMock,
            side_effect=mark_extracted,
        ) as dispatch:
            with TestClient(app) as client:
                response = client.post(f"/api/v1/documents/{DOCUMENT_ID}/extract")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "extracted"
    dispatch.assert_awaited_once_with(document_id=DOCUMENT_ID, tenant_id=TENANT_ID)


def test_extract_document_endpoint_skips_already_extracted_document() -> None:
    upload_db = _UploadDb(rows=[_document_row(status="extracted")])
    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_service_role_client] = lambda: upload_db
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()

    try:
        with patch(
            "app.api.v1.endpoints.documents._dispatch_extraction",
            new_callable=AsyncMock,
        ) as dispatch:
            with TestClient(app) as client:
                response = client.post(f"/api/v1/documents/{DOCUMENT_ID}/extract")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "extracted"
    dispatch.assert_not_awaited()
