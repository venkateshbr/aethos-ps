"""Period lock tests (C27 + close reconciliation).

Covers:
- happy path: admin locks a period; status reflects locked
- double-lock returns 409
- non-admin cannot lock (manager 403) — covered in test_rbac_matrix
- lock rejects when finalized sub-ledger rows are missing GL journals
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from tests.fixtures.scenarios import SeedWorld, make_service_client, mint_jwt

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_accounting,
    pytest.mark.requires_supabase,
]


def _unique_future_period() -> str:
    """A period that's unlikely to collide with another test run.

    We use a year in the 2080s to avoid colliding with real test data and to
    make sweep-clean easy.
    """
    n = uuid.uuid4().int % 12 + 1
    return f"2087-{n:02d}"


@pytest.fixture
def admin_client_a(api_base_url: str, world: SeedWorld) -> httpx.Client:
    """A JWT for an admin user in tenant A."""
    token = mint_jwt(
        user_id=world.tenant_a.owner.user_id,  # reuse the seeded user
        email=world.tenant_a.owner.email,
        role="admin",
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": world.tenant_a.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        yield c


def _cleanup_lock(world: SeedWorld, period: str) -> None:
    """Delete a period_locks row by tenant_id + period (best-effort)."""
    try:
        db = make_service_client()
        db.table("period_locks").delete().eq("tenant_id", world.tenant_a.tenant_id).eq(
            "period", period
        ).execute()
    except Exception:
        pass


def _cleanup_invoice(world: SeedWorld, invoice_id: str) -> None:
    """Delete a test invoice row by tenant + id (best-effort)."""
    try:
        db = make_service_client()
        db.table("invoices").delete().eq("tenant_id", world.tenant_a.tenant_id).eq(
            "id", invoice_id
        ).execute()
    except Exception:
        pass


def test_period_lock_happy_path(admin_client_a: httpx.Client, world: SeedWorld) -> None:
    """Admin locks a fresh period; subsequent list shows it locked."""
    period = _unique_future_period()
    try:
        r1 = admin_client_a.post(f"/api/v1/accounting/periods/{period}/lock")
        assert r1.status_code == 200, r1.text
        assert r1.json()["action"] == "locked"

        # Verify via list endpoint (only returns -12 to +3 months so this period
        # won't show up unless we look at the lock-row directly).
        db = make_service_client()
        row = (
            db.table("period_locks")
            .select("period, locked_by")
            .eq("tenant_id", world.tenant_a.tenant_id)
            .eq("period", period)
            .execute()
        )
        assert row.data, "Lock row not persisted in DB"
    finally:
        _cleanup_lock(world, period)


def test_period_lock_double_returns_409(
    admin_client_a: httpx.Client, world: SeedWorld
) -> None:
    """Locking the same period twice returns 409."""
    period = _unique_future_period()
    try:
        r1 = admin_client_a.post(f"/api/v1/accounting/periods/{period}/lock")
        assert r1.status_code == 200, r1.text

        r2 = admin_client_a.post(f"/api/v1/accounting/periods/{period}/lock")
        assert r2.status_code == 409, (
            f"Expected 409 on double-lock, got {r2.status_code}: {r2.text}"
        )
    finally:
        _cleanup_lock(world, period)


def test_period_lock_invalid_format_returns_422(
    admin_client_a: httpx.Client,
) -> None:
    """Period must match YYYY-MM. Path-safe bad values get 422; values that
    break the path (contain `/`) get 404 from FastAPI's router.

    We accept 422 for the validated-by-handler cases. `2026/05` is excluded
    because it splits the path and reaches a non-existent route.
    """
    for bad in ("2026-13", "26-05", "2026-5", "abc"):
        r = admin_client_a.post(f"/api/v1/accounting/periods/{bad}/lock")
        assert r.status_code == 422, (
            f"Expected 422 for {bad!r}, got {r.status_code}: {r.text}"
        )


def test_period_lock_cross_tenant_isolation(
    admin_client_a: httpx.Client, client_b: httpx.Client, world: SeedWorld
) -> None:
    """Tenant A's lock must not affect tenant B.

    We lock a period in tenant A, then confirm tenant B can still operate
    against the same period string."""
    period = _unique_future_period()
    try:
        r1 = admin_client_a.post(f"/api/v1/accounting/periods/{period}/lock")
        assert r1.status_code == 200, r1.text

        # Tenant B locking the same period should succeed (different tenant)
        # We need an admin JWT for tenant B

        # Mint admin for tenant B owner
        admin_b_token = mint_jwt(
            user_id=world.tenant_b.owner.user_id,
            email=world.tenant_b.owner.email,
            role="admin",
        )
        r2 = client_b.post(
            f"/api/v1/accounting/periods/{period}/lock",
            headers={
                "Authorization": f"Bearer {admin_b_token}",
                "X-Tenant-ID": world.tenant_b.tenant_id,
            },
        )
        # Should be 200 — tenant B's lock is independent of tenant A's
        assert r2.status_code == 200, (
            f"Tenant B blocked from locking period that tenant A locked — "
            f"period_locks should be tenant-scoped. Status: {r2.status_code}, "
            f"body: {r2.text}"
        )
        # Cleanup tenant B's lock
        try:
            db = make_service_client()
            db.table("period_locks").delete().eq(
                "tenant_id", world.tenant_b.tenant_id
            ).eq("period", period).execute()
        except Exception:
            pass
    finally:
        _cleanup_lock(world, period)


def test_period_lock_rejects_when_subledger_unbalanced(
    admin_client_a: httpx.Client, world: SeedWorld
) -> None:
    """A period with a finalized invoice missing its GL journal refuses to lock."""
    period = _unique_future_period()
    invoice_id = str(uuid.uuid4())
    try:
        db = make_service_client()
        db.table("invoices").insert(
            {
                "id": invoice_id,
                "tenant_id": world.tenant_a.tenant_id,
                "engagement_id": world.tenant_a.engagement_ids[0],
                "client_id": world.tenant_a.client_ids[0],
                "currency": world.tenant_a.base_currency,
                "subtotal": "100.00",
                "tax_total": "0.00",
                "total": "100.00",
                "status": "approved",
                "issue_date": f"{period}-15",
                "due_date": f"{period}-28",
                "notes": "period-lock reconciliation regression fixture",
            }
        ).execute()

        r = admin_client_a.post(f"/api/v1/accounting/periods/{period}/lock")
        assert r.status_code == 409, r.text
        detail = r.json()["detail"]
        assert detail["code"] == "close_reconciliation_failed"
        assert detail["findings"][0]["code"] == "missing_invoice_journal"
    finally:
        _cleanup_invoice(world, invoice_id)
        _cleanup_lock(world, period)
