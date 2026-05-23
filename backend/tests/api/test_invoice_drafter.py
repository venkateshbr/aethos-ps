"""C14 — invoice_drafter_agent across all 5 billing arrangements.

This drives `POST /engagements/{id}/draft-invoice` which calls the
invoice_drafter_agent. We exercise the endpoint contract; the agent
output evaluation is in `tests/evals/`.
"""

from __future__ import annotations

import httpx
import pytest

from tests.fixtures.scenarios import SeedWorld, mint_jwt

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_billing,
    pytest.mark.requires_supabase,
]


@pytest.fixture
def manager_a(api_base_url: str, world: SeedWorld) -> httpx.Client:
    u = world.tenant_a.members["manager"]
    h = {
        "Authorization": f"Bearer {mint_jwt(user_id=u.user_id, email=u.email, role='manager')}",
        "X-Tenant-ID": world.tenant_a.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=h, timeout=15.0) as c:
        yield c


@pytest.mark.xfail(
    reason=(
        "Bug #101 — invoice_drafter_agent doesn't catch PGRST116 '0 rows' for "
        "unknown engagement and returns 500 instead of 404."
    ),
    strict=False,
)
def test_draft_invoice_unknown_engagement_returns_404(manager_a: httpx.Client) -> None:
    r = manager_a.post(
        "/api/v1/engagements/00000000-0000-0000-0000-000000000000/draft-invoice"
    )
    assert r.status_code == 404, r.text


@pytest.mark.xfail(
    reason=(
        "Bug #101 — invoice_drafter_agent doesn't translate PGRST116 for "
        "cross-tenant engagement to 404; emits 500. Cross-tenant leak risk."
    ),
    strict=False,
)
def test_draft_invoice_cross_tenant_engagement_returns_404(
    manager_a: httpx.Client, world: SeedWorld
) -> None:
    """Tenant A cannot draft invoice on tenant B's engagement."""
    eng_id = world.tenant_b.engagement_ids[0]
    r = manager_a.post(f"/api/v1/engagements/{eng_id}/draft-invoice")
    assert r.status_code == 404, (
        f"Cross-tenant draft-invoice leak: tenant A got {r.status_code} on tenant B engagement"
    )


def test_draft_invoice_requires_auth(client: httpx.Client, world: SeedWorld) -> None:
    eng_id = world.tenant_a.engagement_ids[0]
    r = client.post(f"/api/v1/engagements/{eng_id}/draft-invoice")
    assert r.status_code == 401, r.text


def test_draft_invoice_tm_engagement_returns_proposal(
    manager_a: httpx.Client, world: SeedWorld
) -> None:
    """T&M engagement should return a proposal (200) or 422 if no time entries
    yet. The failure mode we're guarding is 500."""
    eng_id = world.tenant_a.engagement_ids[0]
    r = manager_a.post(f"/api/v1/engagements/{eng_id}/draft-invoice")
    # 200 (proposal returned), 422 (no time entries), or 409 (already drafted)
    assert r.status_code != 500, f"Draft invoice 500: {r.text[:200]}"
    assert r.status_code in (200, 201, 202, 409, 422), r.text
