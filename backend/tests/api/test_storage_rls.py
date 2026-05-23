"""Storage RLS — defense-in-depth verification for the `documents` bucket.

The API uploads files via the service-role Supabase client, which bypasses
RLS entirely (tenant scoping for writes is enforced by `get_tenant_id`'s
membership check at the API layer).  But if any future surface ever talks
to Storage with an `authenticated`-role JWT — a signed-URL helper, a
direct client upload, or a misconfigured client that picks up the anon key
instead of service-role — RLS is the last line of defence.

These tests exercise that line of defence directly:

  1. Upload as Tenant A via the service-role client (always succeeds).
  2. Read the object as an authenticated client carrying Tenant A's JWT
     — must succeed (membership matches first path segment).
  3. Read the same object as an authenticated client carrying Tenant B's
     JWT — must fail (no membership for that tenant_id).
  4. Read again via the service-role client — must succeed (service-role
     bypasses RLS by design).

These tests are a guard for issue #100.  If they regress, somebody has
either dropped a `documents_tenant_*` policy or removed the
`tenant_users` membership row that the policy relies on.
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest

from tests.fixtures.scenarios import SeedWorld, mint_jwt

pytestmark = [
    pytest.mark.security,
    pytest.mark.multi_tenant,
    pytest.mark.requires_supabase,
]

_MIN_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<<>>>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n"
    b"0000000053 00000 n \n0000000102 00000 n \ntrailer<</Size 4/Root 1 0 R>>\n"
    b"startxref\n170\n%%EOF"
)


def _supabase_env() -> tuple[str, str, str]:
    url = os.environ.get("SUPABASE_URL", "")
    anon = os.environ.get("SUPABASE_ANON_KEY", "")
    service = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not (url and anon and service):
        pytest.skip("SUPABASE_URL / SUPABASE_ANON_KEY / SUPABASE_SERVICE_ROLE_KEY required")
    return url, anon, service


def _storage_object_url(base_url: str, bucket: str, path: str) -> str:
    return f"{base_url}/storage/v1/object/{bucket}/{path}"


def _bearer_for_tenant(world: SeedWorld, *, side: str) -> str:
    """Mint a JWT for the owner of tenant A or B (no API round-trip)."""
    tenant = world.tenant_a if side == "a" else world.tenant_b
    return mint_jwt(user_id=tenant.owner.user_id, email=tenant.owner.email, role="owner")


def test_storage_rls_cross_tenant_denial(world: SeedWorld) -> None:
    """Object at /<tenant_a>/... is readable by A's JWT, blocked for B's JWT,
    and always readable by the service-role key.
    """
    url, anon, service = _supabase_env()

    # ------------------------------------------------------------------
    # 1. Seed an object under Tenant A's prefix using the service-role key.
    # ------------------------------------------------------------------
    object_uuid = uuid.uuid4().hex
    path = f"{world.tenant_a.tenant_id}/2026/05/{object_uuid}.pdf"

    upload_r = httpx.post(
        _storage_object_url(url, "documents", path),
        headers={
            "Authorization": f"Bearer {service}",
            "apikey": service,
            "Content-Type": "application/pdf",
        },
        content=_MIN_PDF,
        timeout=15.0,
    )
    assert upload_r.status_code in (200, 201), (
        f"Service-role upload should succeed; got {upload_r.status_code}: {upload_r.text[:200]}"
    )

    try:
        # ------------------------------------------------------------------
        # 2. Tenant A (correct owner) reads via authenticated JWT — allowed.
        # ------------------------------------------------------------------
        a_token = _bearer_for_tenant(world, side="a")
        r_a = httpx.get(
            _storage_object_url(url, "documents", path),
            headers={"Authorization": f"Bearer {a_token}", "apikey": anon},
            timeout=15.0,
        )
        assert r_a.status_code == 200, (
            f"Tenant A's own object must be readable by A's JWT — "
            f"got {r_a.status_code}: {r_a.text[:200]}"
        )

        # ------------------------------------------------------------------
        # 3. Tenant B reads the same object via authenticated JWT — denied.
        # ------------------------------------------------------------------
        b_token = _bearer_for_tenant(world, side="b")
        r_b = httpx.get(
            _storage_object_url(url, "documents", path),
            headers={"Authorization": f"Bearer {b_token}", "apikey": anon},
            timeout=15.0,
        )
        # Storage typically returns 400/404 for an RLS denial on object GET
        # rather than 403 (it hides existence).  Anything 2xx would be a
        # tenant-isolation breach.
        assert r_b.status_code not in (200, 201, 202, 204), (
            f"CROSS-TENANT BREACH — Tenant B was able to read Tenant A's object! "
            f"status={r_b.status_code} body={r_b.text[:200]}"
        )

        # ------------------------------------------------------------------
        # 4. Service-role read still works (bypasses RLS).
        # ------------------------------------------------------------------
        r_svc = httpx.get(
            _storage_object_url(url, "documents", path),
            headers={"Authorization": f"Bearer {service}", "apikey": service},
            timeout=15.0,
        )
        assert r_svc.status_code == 200, (
            f"Service-role must still bypass RLS; got {r_svc.status_code}: {r_svc.text[:200]}"
        )

    finally:
        # ------------------------------------------------------------------
        # Cleanup — service-role delete (best effort).
        # ------------------------------------------------------------------
        try:
            httpx.delete(
                _storage_object_url(url, "documents", path),
                headers={"Authorization": f"Bearer {service}", "apikey": service},
                timeout=15.0,
            )
        except Exception:
            pass


def test_storage_bucket_config_matches_api(world: SeedWorld) -> None:
    """Guard: bucket config (size cap, MIME allow-list, public flag) stays in
    sync with documents.py.  If this fails, somebody changed one but not the
    other — re-sync via a new migration."""
    url, _, service = _supabase_env()

    r = httpx.get(
        f"{url}/storage/v1/bucket/documents",
        headers={"Authorization": f"Bearer {service}", "apikey": service},
        timeout=15.0,
    )
    assert r.status_code == 200, f"Bucket lookup failed: {r.status_code} {r.text[:200]}"
    cfg = r.json()

    # Mirrors constants in app/api/v1/endpoints/documents.py
    assert cfg["public"] is False, "documents bucket must be private"
    assert cfg["file_size_limit"] == 20 * 1024 * 1024, (
        f"file_size_limit drift: bucket has {cfg['file_size_limit']}, "
        f"API expects {20 * 1024 * 1024}"
    )
    expected_mimes = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
        "text/plain",
    }
    assert set(cfg.get("allowed_mime_types") or []) == expected_mimes, (
        f"MIME allow-list drift: bucket has {cfg.get('allowed_mime_types')}, "
        f"API expects {sorted(expected_mimes)}"
    )
