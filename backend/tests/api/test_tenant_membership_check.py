"""Tenant membership check (issue #90 fix) — focused regression tests.

These complement Aksha's `test_tenant_id_header_spoof_does_not_grant_access`
in `test_multi_tenant_isolation.py`. They exhaustively cover the contract of
the `get_tenant_id` dependency in `app/core/tenant.py`:

| Scenario                                              | Expected |
|-------------------------------------------------------|----------|
| Valid JWT + member's own tenant header                | 200      |
| Valid JWT + foreign tenant header (spoof)             | 404      |
| Valid JWT + missing X-Tenant-ID header                | 403      |
| Valid JWT + malformed (non-UUID) X-Tenant-ID          | 403      |
| Valid JWT + well-formed but unknown tenant UUID       | 404      |
| Missing JWT (any header combo)                        | 401      |
| Malformed JWT (any header combo)                      | 401      |
| Valid JWT + soft-deleted tenant_users row             | 404      |
| Tenant A manager with tenant B header                 | 404      |

Every leak in this table is a P0 — keep this test green forever.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
import pytest

from tests.fixtures.scenarios import (
    SeedWorld,
    auth_headers,
    make_service_client,
    mint_jwt,
)

pytestmark = [
    pytest.mark.api,
    pytest.mark.security,
    pytest.mark.multi_tenant,
    pytest.mark.requires_supabase,
]


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_member_with_own_tenant_header_is_allowed(
    api_base_url: str, world: SeedWorld
) -> None:
    """The seeded owner of tenant A can list tenant A's clients."""
    headers = auth_headers(world.tenant_a, role="owner")
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        r = c.get("/api/v1/clients")
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# Spoof — the headline bug fix from #90
# ---------------------------------------------------------------------------


def test_owner_jwt_with_foreign_tenant_header_is_404(
    api_base_url: str, world: SeedWorld
) -> None:
    """Tenant A's owner sending X-Tenant-ID for tenant B must NOT see B's data."""
    owner = world.tenant_a.owner
    token = mint_jwt(user_id=owner.user_id, email=owner.email, role="owner")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": world.tenant_b.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        r = c.get("/api/v1/clients")
    assert r.status_code == 404, (
        f"P0 SECURITY REGRESSION: tenant A owner with B header got {r.status_code}. "
        f"Body: {r.text[:200]}"
    )


def test_non_owner_member_with_foreign_tenant_header_is_404(
    api_base_url: str, world: SeedWorld
) -> None:
    """A tenant A manager spoofing tenant B's header is also blocked.

    Covers the case where the attacker isn't an owner — same expectation.
    """
    headers = auth_headers(world.tenant_a, role="manager")
    headers["X-Tenant-ID"] = world.tenant_b.tenant_id  # spoof
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        r = c.get("/api/v1/clients")
    assert r.status_code == 404, r.text


# ---------------------------------------------------------------------------
# Header malformation / absence
# ---------------------------------------------------------------------------


def test_missing_x_tenant_id_header_is_403(
    api_base_url: str, world: SeedWorld
) -> None:
    """Valid JWT but no X-Tenant-ID header at all → 403 (existing contract)."""
    owner = world.tenant_a.owner
    token = mint_jwt(user_id=owner.user_id, email=owner.email, role="owner")
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        r = c.get("/api/v1/clients")
    assert r.status_code == 403, r.text


def test_malformed_uuid_x_tenant_id_is_403(
    api_base_url: str, world: SeedWorld
) -> None:
    """A non-UUID X-Tenant-ID must be rejected without hitting the DB."""
    owner = world.tenant_a.owner
    token = mint_jwt(user_id=owner.user_id, email=owner.email, role="owner")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": "not-a-uuid",
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        r = c.get("/api/v1/clients")
    assert r.status_code == 403, r.text


def test_unknown_tenant_uuid_is_404(
    api_base_url: str, world: SeedWorld
) -> None:
    """Well-formed UUID for a tenant that doesn't exist → 404 (membership fails)."""
    owner = world.tenant_a.owner
    token = mint_jwt(user_id=owner.user_id, email=owner.email, role="owner")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(uuid.uuid4()),  # random, no row in tenants
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        r = c.get("/api/v1/clients")
    assert r.status_code == 404, r.text


# ---------------------------------------------------------------------------
# JWT validity
# ---------------------------------------------------------------------------


def test_missing_jwt_is_401(api_base_url: str, world: SeedWorld) -> None:
    """No Authorization header at all → 401 (auth precedes tenant check)."""
    headers = {"X-Tenant-ID": world.tenant_a.tenant_id}
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        r = c.get("/api/v1/clients")
    assert r.status_code == 401, r.text


def test_malformed_jwt_is_401(api_base_url: str, world: SeedWorld) -> None:
    """A garbage bearer token must 401, not 403/404."""
    headers = {
        "Authorization": "Bearer not.a.jwt",
        "X-Tenant-ID": world.tenant_a.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        r = c.get("/api/v1/clients")
    assert r.status_code == 401, r.text


def test_jwt_signed_with_wrong_secret_is_401(
    api_base_url: str, world: SeedWorld
) -> None:
    """A structurally valid JWT signed with the wrong secret must 401.

    Defense against someone fabricating a JWT for an arbitrary user_id.
    """
    from jose import jwt as jose_jwt

    bad_token = jose_jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "email": "attacker@example.com",
            "role": "authenticated",
            "exp": int(datetime.now(UTC).timestamp()) + 3600,
        },
        "the-wrong-secret",
        algorithm="HS256",
    )
    headers = {
        "Authorization": f"Bearer {bad_token}",
        "X-Tenant-ID": world.tenant_a.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        r = c.get("/api/v1/clients")
    assert r.status_code == 401, r.text


# ---------------------------------------------------------------------------
# Soft-deleted membership — revocation must take effect
# ---------------------------------------------------------------------------


def test_soft_deleted_tenant_user_is_blocked(
    api_base_url: str, world: SeedWorld
) -> None:
    """A user whose tenant_users row is soft-deleted (deleted_at NOT NULL)
    must lose access immediately on the next request.

    Setup: insert a fresh user into tenant A, hit /clients to confirm 200,
    then soft-delete and confirm 404.

    Important: we use a brand-new user so we don't corrupt the seeded owner
    that other tests depend on.
    """
    db = make_service_client()
    revoked_user_id = str(uuid.uuid4())
    revoked_email = f"revoked-{uuid.uuid4().hex[:6]}@aksha.test"

    # Insert a fresh tenant_users row for tenant A.
    insert_res = (
        db.table("tenant_users")
        .insert(
            {
                "tenant_id": world.tenant_a.tenant_id,
                "user_id": revoked_user_id,
                "role": "member",
                "joined_at": datetime.now(UTC).isoformat(),
            }
        )
        .execute()
    )
    membership_id = insert_res.data[0]["id"]

    token = mint_jwt(user_id=revoked_user_id, email=revoked_email, role="member")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": world.tenant_a.tenant_id,
    }

    try:
        # Sanity: while active, access works.
        with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
            r_before = c.get("/api/v1/clients")
        assert r_before.status_code == 200, (
            f"Setup failure: fresh member couldn't read /clients. "
            f"Status {r_before.status_code}: {r_before.text[:200]}"
        )

        # Soft-delete the membership.
        db.table("tenant_users").update(
            {"deleted_at": datetime.now(UTC).isoformat()}
        ).eq("id", membership_id).execute()

        # Next request must be blocked — no caching allowed.
        with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
            r_after = c.get("/api/v1/clients")
        assert r_after.status_code == 404, (
            f"Revoked user still has access (status {r_after.status_code}). "
            f"Membership check must honour deleted_at IS NOT NULL. "
            f"Body: {r_after.text[:200]}"
        )
    finally:
        # Hard-delete the test row so we don't pollute the seeded world.
        try:
            db.table("tenant_users").delete().eq("id", membership_id).execute()
        except Exception:
            pass
