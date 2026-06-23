"""C10 — Documents upload + listing.

Smoke tests for POST /documents/upload — happy path with a small PDF,
unsupported MIME, oversized file (declined upstream by FastAPI if size limit).
"""

from __future__ import annotations

import io

import httpx
import pytest

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_hitl,
    pytest.mark.requires_supabase,
]


# Minimal valid PDF — 1-page empty PDF, ~470 bytes
_MIN_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<<>>>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000102 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n170\n%%EOF"
)


def test_upload_pdf_document_happy_path(client_a: httpx.Client) -> None:
    files = {"file": ("test.pdf", io.BytesIO(_MIN_PDF), "application/pdf")}
    data = {"kind": "receipt"}
    r = client_a.post("/api/v1/documents/upload", files=files, data=data, timeout=90.0)
    # 200/201 = accepted; 202 = queued for extraction
    assert r.status_code in (200, 201, 202), r.text


def test_upload_requires_auth(client: httpx.Client) -> None:
    files = {"file": ("test.pdf", io.BytesIO(_MIN_PDF), "application/pdf")}
    r = client.post("/api/v1/documents/upload", files=files, data={"kind": "receipt"})
    assert r.status_code == 401, r.text


def test_upload_unsupported_mime_rejected(client_a: httpx.Client) -> None:
    """Executable / script MIMEs must be rejected, not silently stored."""
    files = {"file": ("evil.exe", io.BytesIO(b"MZ\x90\x00fake"), "application/x-msdownload")}
    data = {"kind": "receipt"}
    r = client_a.post("/api/v1/documents/upload", files=files, data=data)
    # 415 (unsupported media type) or 422 (validation) — anything but 2xx success
    assert r.status_code in (400, 415, 422), (
        f"Executable upload accepted: {r.status_code}, body={r.text[:200]}"
    )
