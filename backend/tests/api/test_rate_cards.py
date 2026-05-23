"""C8 — Rate cards CRUD.

Light coverage — list, get, create (when supported), cross-tenant isolation.
"""

from __future__ import annotations

import httpx
import pytest

from tests.fixtures.scenarios import SeedWorld

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_engagement,
    pytest.mark.requires_supabase,
]


def test_list_rate_cards_tenant_scoped(client_a: httpx.Client, world: SeedWorld) -> None:
    r = client_a.get("/api/v1/rate-cards")
    assert r.status_code == 200, r.text
    body = r.json()
    rows = body.get("items", body) if isinstance(body, dict) else body
    if isinstance(rows, list):
        for row in rows:
            assert row.get("tenant_id") == world.tenant_a.tenant_id, (
                f"Cross-tenant rate card leak: {row}"
            )


def test_list_rate_cards_requires_auth(client: httpx.Client) -> None:
    r = client.get("/api/v1/rate-cards")
    assert r.status_code == 401, r.text


def test_get_unknown_rate_card_returns_404(client_a: httpx.Client) -> None:
    r = client_a.get("/api/v1/rate-cards/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404, r.text
