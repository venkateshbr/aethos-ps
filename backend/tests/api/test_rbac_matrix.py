"""RBAC matrix tests (C32).

For each role x action cell, verify the response code matches the spec:
- owner > admin > manager > member > viewer
- viewer and member can only READ
- manager can create clients, engagements, projects
- admin can change engagement status, lock period
- only owner can connect Stripe, change subscription

Each failure in this file is a P0 if it grants more access than spec, P1 if it
denies legitimate access.
"""

from __future__ import annotations

import httpx
import pytest

pytestmark = [
    pytest.mark.api,
    pytest.mark.rbac,
    pytest.mark.security,
    pytest.mark.requires_supabase,
]


# ---------------------------------------------------------------------------
# Viewer — read only
# ---------------------------------------------------------------------------


def test_viewer_can_list_clients(client_a_viewer: httpx.Client) -> None:
    r = client_a_viewer.get("/api/v1/clients")
    assert r.status_code == 200, r.text


def test_viewer_cannot_create_client(client_a_viewer: httpx.Client) -> None:
    r = client_a_viewer.post(
        "/api/v1/clients",
        json={"name": "Hacker Co", "kind": "customer", "currency": "USD"},
    )
    assert r.status_code == 403, (
        f"RBAC GAP: viewer was allowed to create a client (status {r.status_code}). "
        f"Body: {r.text[:200]}"
    )


def test_viewer_cannot_create_engagement(
    client_a_viewer: httpx.Client, world
) -> None:
    r = client_a_viewer.post(
        "/api/v1/engagements",
        json={
            "client_id": world.tenant_a.client_ids[0],
            "name": "Hacker Engagement",
            "billing_arrangement": "time_and_materials",
            "currency": "USD",
        },
    )
    assert r.status_code == 403, r.text


# ---------------------------------------------------------------------------
# Manager — can create commercial entities, cannot lock period
# ---------------------------------------------------------------------------


def test_manager_can_list_engagements(client_a_manager: httpx.Client) -> None:
    r = client_a_manager.get("/api/v1/engagements")
    assert r.status_code == 200, r.text


def test_manager_cannot_lock_period(client_a_manager: httpx.Client) -> None:
    r = client_a_manager.post("/api/v1/accounting/periods/2099-01/lock")
    assert r.status_code == 403, (
        f"RBAC GAP: manager allowed to lock a period (status {r.status_code}). "
        f"Lock is admin-only per accounting.py:148."
    )


def test_manager_cannot_change_engagement_status(
    client_a_manager: httpx.Client, world
) -> None:
    eng_id = world.tenant_a.engagement_ids[0]
    r = client_a_manager.patch(
        f"/api/v1/engagements/{eng_id}/status",
        json={"status": "completed"},
    )
    assert r.status_code == 403, (
        f"RBAC GAP: manager allowed to change engagement status (status {r.status_code})"
    )


# ---------------------------------------------------------------------------
# Admin — can lock period, change engagement status; cannot connect Stripe
# ---------------------------------------------------------------------------


def test_admin_role_below_owner_cannot_connect_stripe(
    api_base_url: str, world
) -> None:
    """Only owner may initiate Stripe Connect OAuth."""
    from tests.fixtures.scenarios import mint_jwt

    # Mint an admin JWT for the seeded owner's user_id (different role claim)
    admin_token = mint_jwt(
        user_id=world.tenant_a.members.get("manager", world.tenant_a.owner).user_id,
        email="admin-test@aksha.test",
        role="admin",
    )
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "X-Tenant-ID": world.tenant_a.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        r = c.get("/api/v1/stripe/connect/oauth-url")
    assert r.status_code == 403, (
        f"RBAC GAP: admin allowed to initiate Stripe Connect (status {r.status_code}). "
        f"Only owner may per stripe_connect.py:47."
    )


# ---------------------------------------------------------------------------
# Unknown role coerces to lowest (viewer)
# ---------------------------------------------------------------------------


def test_unknown_role_treated_as_viewer(api_base_url: str, world) -> None:
    """Per rbac.py:60-63, unknown role enum value coerces to viewer."""
    from tests.fixtures.scenarios import mint_jwt

    weird_token = mint_jwt(
        user_id=world.tenant_a.owner.user_id,
        email=world.tenant_a.owner.email,
        role="superduperadmin",  # not in enum
    )
    headers = {
        "Authorization": f"Bearer {weird_token}",
        "X-Tenant-ID": world.tenant_a.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        # Read should succeed (viewer can read)
        r_get = c.get("/api/v1/clients")
        assert r_get.status_code == 200, r_get.text
        # Write should 403 (viewer cannot write)
        r_post = c.post(
            "/api/v1/clients",
            json={"name": "Bogus", "kind": "customer", "currency": "USD"},
        )
        assert r_post.status_code == 403, (
            f"RBAC GAP: unknown role granted write access (status {r_post.status_code})"
        )
