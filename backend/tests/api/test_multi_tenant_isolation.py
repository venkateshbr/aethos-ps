"""Cross-tenant data isolation tests.

C31 from `docs/qa/MASTER_TEST_PLAN.md`. RLS is supposed to prevent tenant A's
JWT from reading or mutating any of tenant B's rows. Every leak here is a P0.

For each entity:
- list endpoint returns ZERO of tenant B's rows when called as tenant A
- detail endpoint on a tenant B id returns 404 (NOT 200 with leaked row)
- update / delete on a tenant B id returns 404 (NOT 200)
"""

from __future__ import annotations

import httpx
import pytest

from tests.fixtures.scenarios import SeedWorld

pytestmark = [
    pytest.mark.api,
    pytest.mark.multi_tenant,
    pytest.mark.security,
    pytest.mark.requires_supabase,
]


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------


def test_clients_list_does_not_leak_tenant_b(
    client_a: httpx.Client, world: SeedWorld
) -> None:
    """Tenant A's /clients list must exclude every Tenant B client id."""
    r = client_a.get("/api/v1/clients")
    assert r.status_code == 200, r.text
    ids = {c["id"] for c in r.json().get("clients", [])}
    leaked = ids & set(world.tenant_b.client_ids + world.tenant_b.vendor_ids)
    assert not leaked, f"Cross-tenant leak: {leaked} appeared in tenant A's list"


def test_clients_get_returns_404_for_tenant_b_id(
    client_a: httpx.Client, world: SeedWorld
) -> None:
    """Direct GET on tenant B's client id from tenant A must be 404."""
    target = world.tenant_b.client_ids[0]
    r = client_a.get(f"/api/v1/clients/{target}")
    assert r.status_code == 404, (
        f"Cross-tenant data leak: tenant A got {r.status_code} on tenant B id {target}. "
        f"Body: {r.text}"
    )


def test_clients_patch_returns_404_for_tenant_b_id(
    client_a: httpx.Client, world: SeedWorld
) -> None:
    """Update on tenant B's client id must 404, not silently mutate."""
    target = world.tenant_b.client_ids[0]
    r = client_a.patch(f"/api/v1/clients/{target}", json={"name": "PWNED"})
    assert r.status_code == 404, r.text


# ---------------------------------------------------------------------------
# Engagements
# ---------------------------------------------------------------------------


def test_engagements_list_does_not_leak_tenant_b(
    client_a: httpx.Client, world: SeedWorld
) -> None:
    r = client_a.get("/api/v1/engagements")
    assert r.status_code == 200, r.text
    body = r.json()
    rows = body if isinstance(body, list) else body.get("engagements", body.get("items", []))
    ids = {e["id"] for e in rows}
    leaked = ids & set(world.tenant_b.engagement_ids)
    assert not leaked, f"Cross-tenant engagement leak: {leaked}"


def test_engagements_get_returns_404_for_tenant_b_id(
    client_a: httpx.Client, world: SeedWorld
) -> None:
    target = world.tenant_b.engagement_ids[0]
    r = client_a.get(f"/api/v1/engagements/{target}")
    assert r.status_code == 404, (
        f"Cross-tenant data leak: tenant A read tenant B engagement {target}. "
        f"Status {r.status_code}, body: {r.text}"
    )


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


def test_projects_list_does_not_leak_tenant_b(
    client_a: httpx.Client, world: SeedWorld
) -> None:
    """List projects scoped to tenant A's engagement — tenant B's project ids
    must never appear, even though we're using a known engagement filter.

    Bug #91 — `engagement_id` is required, there is no top-level tenant-scoped
    list endpoint. We test the scoped version here to still cover RLS.
    """
    eng_id = world.tenant_a.engagement_ids[0]
    r = client_a.get(f"/api/v1/projects?engagement_id={eng_id}")
    assert r.status_code == 200, r.text
    body = r.json()
    rows = body if isinstance(body, list) else body.get("projects", body.get("items", []))
    ids = {p["id"] for p in rows}
    leaked = ids & set(world.tenant_b.project_ids)
    assert not leaked, f"Cross-tenant project leak via scoped list: {leaked}"


def test_projects_list_with_tenant_b_engagement_returns_empty(
    client_a: httpx.Client, world: SeedWorld
) -> None:
    """Tenant A querying with tenant B's engagement_id must NOT return any
    rows (RLS denies). Status 200 + empty is acceptable; 404 also acceptable."""
    other_eng = world.tenant_b.engagement_ids[0]
    r = client_a.get(f"/api/v1/projects?engagement_id={other_eng}")
    assert r.status_code in (200, 404), r.text
    if r.status_code == 200:
        body = r.json()
        rows = body if isinstance(body, list) else body.get("projects", body.get("items", []))
        assert rows == [], (
            f"Cross-tenant data leak: tenant A queried with tenant B engagement "
            f"and got {len(rows)} rows back. Body: {r.text[:300]}"
        )


def test_projects_get_returns_404_for_tenant_b_id(
    client_a: httpx.Client, world: SeedWorld
) -> None:
    target = world.tenant_b.project_ids[0]
    r = client_a.get(f"/api/v1/projects/{target}")
    assert r.status_code == 404, r.text


# ---------------------------------------------------------------------------
# Tenant-header spoofing — JWT for tenant A user, but X-Tenant-ID = tenant B
# ---------------------------------------------------------------------------


def test_tenant_id_header_spoof_does_not_grant_access(
    api_base_url: str, world: SeedWorld
) -> None:
    """A tenant A user who lies and sends X-Tenant-ID of tenant B should not
    suddenly see tenant B data.

    Today the backend uses the X-Tenant-ID header without verifying that the
    JWT subject is a member of the claimed tenant (see `app/core/tenant.py`
    TODO). If this test fails, it's a P0 — a malicious user can read any
    tenant's data by guessing the tenant_id (UUIDs make this hard but not
    impossible if leaked elsewhere).
    """
    from tests.fixtures.scenarios import mint_jwt

    # Mint a JWT for tenant A's owner
    a_owner = world.tenant_a.owner
    token = mint_jwt(user_id=a_owner.user_id, email=a_owner.email, role="owner")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": world.tenant_b.tenant_id,  # spoofed
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        r = c.get("/api/v1/clients")
    # Today this is expected to FAIL (return tenant B's clients) until the
    # backend cross-checks membership. We assert what SHOULD happen: 403/404.
    assert r.status_code in (
        403,
        404,
    ), (
        f"P0 SECURITY: X-Tenant-ID spoof returned {r.status_code} for a user "
        f"who isn't a member of the claimed tenant. Body: {r.text[:200]}"
    )
