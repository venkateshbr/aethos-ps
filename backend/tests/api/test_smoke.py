"""Smoke tests for the Aksha QA suite — proves the fixtures wire up.

If any of these fail, every other api/* test will fail too. Fix them first.
"""

from __future__ import annotations

import httpx
import pytest

from tests.fixtures.scenarios import SeedWorld

pytestmark = [pytest.mark.api, pytest.mark.requires_supabase]


@pytest.mark.smoke
def test_api_health(client: httpx.Client) -> None:
    """The API root health endpoint responds."""
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"


@pytest.mark.smoke
def test_api_health_ready_db_ok(client: httpx.Client) -> None:
    """Readiness probe reports a healthy DB.

    Note: this hits real Supabase. A failure here means the tests cannot trust
    any DB-side assertion — block the whole run.
    """
    r = client.get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["checks"]["db"]["status"] == "ok", body


@pytest.mark.smoke
def test_world_seeds_two_isolated_tenants(world: SeedWorld) -> None:
    """The seeded world has two distinct tenants with different currencies."""
    assert world.tenant_a.tenant_id != world.tenant_b.tenant_id
    assert world.tenant_a.base_currency == "USD"
    assert world.tenant_b.base_currency == "GBP"
    assert world.tenant_a.engagement_ids
    assert world.tenant_b.engagement_ids


@pytest.mark.smoke
def test_owner_jwt_passes_through_auth(client_a: httpx.Client) -> None:
    """A JWT minted with the seeded owner reaches authed routes (any 2xx/4xx
    that isn't a 401 is good enough — we're proving the bearer is accepted)."""
    r = client_a.get("/api/v1/clients")
    assert r.status_code != 401, r.text
    assert r.status_code != 403, r.text


@pytest.mark.smoke
def test_missing_jwt_returns_401(client: httpx.Client) -> None:
    """Without auth, /api/v1/clients must 401."""
    r = client.get("/api/v1/clients", headers={"X-Tenant-ID": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 401, r.text
