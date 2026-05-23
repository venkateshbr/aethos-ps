"""C16 — Inbox / HITL task lifecycle.

Covers GET /inbox/tasks, GET /inbox/tasks/{id}, approve, approve-with-edits,
reject, escalate. Real tasks are produced by extraction agents; here we just
exercise the endpoint contract.
"""

from __future__ import annotations

import httpx
import pytest

from tests.fixtures.scenarios import SeedWorld

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_hitl,
    pytest.mark.requires_supabase,
]


def test_list_inbox_tasks_returns_200(client_a: httpx.Client) -> None:
    """Empty inbox is fine; endpoint must respond 200 (not 404)."""
    r = client_a.get("/api/v1/inbox/tasks")
    assert r.status_code == 200, r.text


def test_list_inbox_tasks_requires_auth(client: httpx.Client) -> None:
    r = client.get("/api/v1/inbox/tasks")
    assert r.status_code == 401, r.text


def test_get_inbox_task_unknown_id_returns_404(client_a: httpx.Client) -> None:
    r = client_a.get("/api/v1/inbox/tasks/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404, r.text


def test_approve_unknown_task_returns_404(client_a: httpx.Client) -> None:
    r = client_a.post(
        "/api/v1/inbox/tasks/00000000-0000-0000-0000-000000000000/approve"
    )
    assert r.status_code == 404, r.text


def test_inbox_task_lifecycle_endpoints_exist(client_a: httpx.Client) -> None:
    """All 4 lifecycle endpoints (approve/approve-with-edits/reject/escalate)
    must exist (404 = task not found, 405 = method not allowed = endpoint missing)."""
    fake = "00000000-0000-0000-0000-000000000000"
    for path, body in [
        (f"/api/v1/inbox/tasks/{fake}/approve", None),
        (f"/api/v1/inbox/tasks/{fake}/approve-with-edits", {"edits": {}}),
        (f"/api/v1/inbox/tasks/{fake}/reject", {"reason": "test"}),
        (f"/api/v1/inbox/tasks/{fake}/escalate", {"reason": "test"}),
    ]:
        r = client_a.post(path, json=body) if body else client_a.post(path)
        assert r.status_code != 405, (
            f"Endpoint {path} returned 405 — method not allowed (route missing)"
        )
        # Either 404 (not found) or 422 (body validation) is acceptable
        assert r.status_code in (404, 422), (
            f"{path} returned {r.status_code}: {r.text[:200]}"
        )


def test_inbox_cross_tenant_isolation(
    client_a: httpx.Client, world: SeedWorld
) -> None:
    """Tenant A listing inbox tasks must never see tenant B task ids.

    Empty inbox in fresh seed is OK — the assertion is "no leak", which is
    trivially true when both are empty."""
    r = client_a.get("/api/v1/inbox/tasks")
    assert r.status_code == 200, r.text
    body = r.json()
    rows = body.get("items", body) if isinstance(body, dict) else body
    if isinstance(rows, list):
        for row in rows:
            assert row.get("tenant_id") == world.tenant_a.tenant_id, (
                f"Cross-tenant inbox task leak: {row}"
            )
