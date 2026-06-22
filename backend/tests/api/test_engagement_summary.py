"""Tests for GET /api/v1/engagements/{id}/summary.

Coverage
--------
C1 — Freshly-created engagement with no invoices or time entries returns
     billed_to_date="0.00", wip_hours=0.0, wip_value="0.00", invoice_count=0.

C2 — After posting an approved invoice the billed_to_date increases and
     invoice_count == 1.

C3 — Voided invoices are excluded from billed_to_date.

C4 — Draft invoices are excluded from billed_to_date.

C5 — remaining_value is present for a fixed_fee engagement and equals
     total_value - billed_to_date.

C6 — remaining_value is None for a pure T&M engagement (no total_value).

C7 — Viewer role can call the endpoint (GET is open to all authenticated users).

C8 — 404 is returned for an unknown engagement id.

C9 — Tenant B cannot see Tenant A's engagement summary (cross-tenant isolation).

C10 — billed_pct is computed correctly from billed / total.

C11 — WIP hours accumulate from unbilled billable time entries across projects.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import pytest

from tests.fixtures.scenarios import SeedWorld, make_service_client, mint_jwt

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_engagement,
    pytest.mark.requires_supabase,
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _today() -> str:
    return date.today().isoformat()


def _seed_invoice(
    db,
    *,
    tenant_id: str,
    engagement_id: str,
    client_id: str,
    total: str,
    status: str = "approved",
) -> str:
    """Insert a minimal invoice row; return its id."""
    res = (
        db.table("invoices")
        .insert(
            {
                "tenant_id": tenant_id,
                "engagement_id": engagement_id,
                "client_id": client_id,
                "currency": "USD",
                "subtotal": total,
                "tax_total": "0.00",
                "total": total,
                "status": status,
                "issue_date": _today(),
            }
        )
        .execute()
    )
    return res.data[0]["id"]


def _seed_time_entry(
    db,
    *,
    tenant_id: str,
    project_id: str,
    employee_id: str,
    hours: str,
    billable: bool = True,
    billing_status: str = "unbilled",
) -> str:
    """Insert a minimal time entry; return its id."""
    res = (
        db.table("time_entries")
        .insert(
            {
                "tenant_id": tenant_id,
                "project_id": project_id,
                "employee_id": employee_id,
                "date": _today(),
                "hours": hours,
                "billable": billable,
                "billing_status": billing_status,
            }
        )
        .execute()
    )
    return res.data[0]["id"]


def _seed_engagement(
    db,
    *,
    tenant_id: str,
    client_id: str,
    billing_arrangement: str = "time_and_materials",
    total_value: str | None = None,
    run_id: str,
) -> str:
    payload: dict = {
        "tenant_id": tenant_id,
        "client_id": client_id,
        "name": f"Summary test eng {run_id} {uuid.uuid4().hex[:6]}",
        "billing_arrangement": billing_arrangement,
        "status": "active",
        "currency": "USD",
    }
    if total_value is not None:
        payload["total_value"] = total_value
    res = db.table("engagements").insert(payload).execute()
    return res.data[0]["id"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def viewer_client(api_base_url: str, world: SeedWorld) -> httpx.Client:
    user = world.tenant_a.members["viewer"]
    token = mint_jwt(user_id=user.user_id, email=user.email, role="viewer")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": world.tenant_a.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        yield c


@pytest.fixture
def owner_client_a(api_base_url: str, world: SeedWorld) -> httpx.Client:
    user = world.tenant_a.owner
    token = mint_jwt(user_id=user.user_id, email=user.email, role="owner")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": world.tenant_a.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        yield c


@pytest.fixture
def owner_client_b(api_base_url: str, world: SeedWorld) -> httpx.Client:
    user = world.tenant_b.owner
    token = mint_jwt(user_id=user.user_id, email=user.email, role="owner")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": world.tenant_b.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        yield c


# ---------------------------------------------------------------------------
# C1 — Fresh engagement, all zeros
# ---------------------------------------------------------------------------


def test_summary_fresh_engagement_all_zeros(
    owner_client_a: httpx.Client, world: SeedWorld
) -> None:
    """A new engagement with no invoices or time entries returns zero financials."""
    db = make_service_client()
    eng_id = _seed_engagement(
        db,
        tenant_id=world.tenant_a.tenant_id,
        client_id=world.tenant_a.client_ids[0],
        billing_arrangement="time_and_materials",
        run_id=world.run_id,
    )

    r = owner_client_a.get(f"/api/v1/engagements/{eng_id}/summary")
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["engagement_id"] == eng_id
    assert Decimal(body["billed_to_date"]) == Decimal("0.00")
    assert body["invoice_count"] == 0
    assert body["wip_hours"] == 0.0
    assert Decimal(body["wip_value"]) == Decimal("0.00")
    assert body["last_invoice_date"] is None
    assert body["total_value"] is None
    assert body["remaining_value"] is None
    assert body["billed_pct"] is None


# ---------------------------------------------------------------------------
# C2 — Approved invoice increases billed_to_date
# ---------------------------------------------------------------------------


def test_summary_approved_invoice_counted(
    owner_client_a: httpx.Client, world: SeedWorld
) -> None:
    db = make_service_client()
    eng_id = _seed_engagement(
        db,
        tenant_id=world.tenant_a.tenant_id,
        client_id=world.tenant_a.client_ids[0],
        billing_arrangement="time_and_materials",
        run_id=world.run_id,
    )
    _seed_invoice(
        db,
        tenant_id=world.tenant_a.tenant_id,
        engagement_id=eng_id,
        client_id=world.tenant_a.client_ids[0],
        total="5000.00",
        status="approved",
    )

    r = owner_client_a.get(f"/api/v1/engagements/{eng_id}/summary")
    assert r.status_code == 200, r.text
    body = r.json()

    assert Decimal(body["billed_to_date"]) == Decimal("5000.00")
    assert body["invoice_count"] == 1
    assert body["last_invoice_date"] == _today()


# ---------------------------------------------------------------------------
# C3 — Voided invoices excluded
# ---------------------------------------------------------------------------


def test_summary_voided_invoice_excluded(
    owner_client_a: httpx.Client, world: SeedWorld
) -> None:
    db = make_service_client()
    eng_id = _seed_engagement(
        db,
        tenant_id=world.tenant_a.tenant_id,
        client_id=world.tenant_a.client_ids[0],
        billing_arrangement="time_and_materials",
        run_id=world.run_id,
    )
    _seed_invoice(
        db,
        tenant_id=world.tenant_a.tenant_id,
        engagement_id=eng_id,
        client_id=world.tenant_a.client_ids[0],
        total="9999.00",
        status="voided",
    )

    r = owner_client_a.get(f"/api/v1/engagements/{eng_id}/summary")
    assert r.status_code == 200, r.text
    body = r.json()

    assert Decimal(body["billed_to_date"]) == Decimal("0.00"), (
        f"Voided invoice should not count: {body}"
    )
    assert body["invoice_count"] == 0


# ---------------------------------------------------------------------------
# C4 — Draft invoices excluded
# ---------------------------------------------------------------------------


def test_summary_draft_invoice_excluded(
    owner_client_a: httpx.Client, world: SeedWorld
) -> None:
    db = make_service_client()
    eng_id = _seed_engagement(
        db,
        tenant_id=world.tenant_a.tenant_id,
        client_id=world.tenant_a.client_ids[0],
        billing_arrangement="time_and_materials",
        run_id=world.run_id,
    )
    _seed_invoice(
        db,
        tenant_id=world.tenant_a.tenant_id,
        engagement_id=eng_id,
        client_id=world.tenant_a.client_ids[0],
        total="3000.00",
        status="draft",
    )

    r = owner_client_a.get(f"/api/v1/engagements/{eng_id}/summary")
    assert r.status_code == 200, r.text
    body = r.json()

    assert Decimal(body["billed_to_date"]) == Decimal("0.00"), (
        f"Draft invoice should not count: {body}"
    )
    assert body["invoice_count"] == 0


# ---------------------------------------------------------------------------
# C5 — remaining_value for fixed_fee engagement
# ---------------------------------------------------------------------------


def test_summary_remaining_value_fixed_fee(
    owner_client_a: httpx.Client, world: SeedWorld
) -> None:
    db = make_service_client()
    eng_id = _seed_engagement(
        db,
        tenant_id=world.tenant_a.tenant_id,
        client_id=world.tenant_a.client_ids[0],
        billing_arrangement="fixed_fee",
        total_value="100000.00",
        run_id=world.run_id,
    )
    _seed_invoice(
        db,
        tenant_id=world.tenant_a.tenant_id,
        engagement_id=eng_id,
        client_id=world.tenant_a.client_ids[0],
        total="40000.00",
        status="paid",
    )

    r = owner_client_a.get(f"/api/v1/engagements/{eng_id}/summary")
    assert r.status_code == 200, r.text
    body = r.json()

    assert Decimal(body["total_value"]) == Decimal("100000.00")
    assert Decimal(body["billed_to_date"]) == Decimal("40000.00")
    assert Decimal(body["remaining_value"]) == Decimal("60000.00"), (
        f"remaining_value wrong: {body}"
    )
    assert body["billed_pct"] == pytest.approx(40.0, rel=1e-2)


# ---------------------------------------------------------------------------
# C6 — remaining_value None for T&M (no total_value)
# ---------------------------------------------------------------------------


def test_summary_no_remaining_value_for_tm(
    owner_client_a: httpx.Client, world: SeedWorld
) -> None:
    db = make_service_client()
    eng_id = _seed_engagement(
        db,
        tenant_id=world.tenant_a.tenant_id,
        client_id=world.tenant_a.client_ids[0],
        billing_arrangement="time_and_materials",
        total_value=None,
        run_id=world.run_id,
    )

    r = owner_client_a.get(f"/api/v1/engagements/{eng_id}/summary")
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["total_value"] is None
    assert body["remaining_value"] is None
    assert body["billed_pct"] is None


# ---------------------------------------------------------------------------
# C7 — Viewer can read the summary (GET is open to all authenticated users)
# ---------------------------------------------------------------------------


def test_summary_accessible_by_viewer(
    viewer_client: httpx.Client, world: SeedWorld
) -> None:
    eng_id = world.tenant_a.engagement_ids[0]
    r = viewer_client.get(f"/api/v1/engagements/{eng_id}/summary")
    assert r.status_code == 200, (
        f"Viewer should be able to GET summary — got {r.status_code}: {r.text}"
    )


# ---------------------------------------------------------------------------
# C8 — 404 for unknown engagement id
# ---------------------------------------------------------------------------


def test_summary_unknown_engagement_returns_404(owner_client_a: httpx.Client) -> None:
    random_id = str(uuid.uuid4())
    r = owner_client_a.get(f"/api/v1/engagements/{random_id}/summary")
    assert r.status_code == 404, r.text


# ---------------------------------------------------------------------------
# C9 — Cross-tenant isolation: Tenant B cannot see Tenant A's summary
# ---------------------------------------------------------------------------


def test_summary_cross_tenant_isolation(
    owner_client_b: httpx.Client, world: SeedWorld
) -> None:
    """Tenant B's authenticated client must not see Tenant A's engagement."""
    eng_id = world.tenant_a.engagement_ids[0]
    r = owner_client_b.get(f"/api/v1/engagements/{eng_id}/summary")
    # The endpoint should return 404 because the RLS-scoped repo filters by tenant.
    assert r.status_code == 404, (
        f"Cross-tenant summary leak detected: status={r.status_code} body={r.text[:200]}"
    )


# ---------------------------------------------------------------------------
# C10 — billed_pct calculation
# ---------------------------------------------------------------------------


def test_summary_billed_pct_calculation(
    owner_client_a: httpx.Client, world: SeedWorld
) -> None:
    db = make_service_client()
    eng_id = _seed_engagement(
        db,
        tenant_id=world.tenant_a.tenant_id,
        client_id=world.tenant_a.client_ids[0],
        billing_arrangement="fixed_fee",
        total_value="200000.00",
        run_id=world.run_id,
    )
    # Bill 50% — two invoices of 50k each
    for _ in range(2):
        _seed_invoice(
            db,
            tenant_id=world.tenant_a.tenant_id,
            engagement_id=eng_id,
            client_id=world.tenant_a.client_ids[0],
            total="50000.00",
            status="sent",
        )

    r = owner_client_a.get(f"/api/v1/engagements/{eng_id}/summary")
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["invoice_count"] == 2
    assert Decimal(body["billed_to_date"]) == Decimal("100000.00")
    assert body["billed_pct"] == pytest.approx(50.0, rel=1e-2)


# ---------------------------------------------------------------------------
# C11 — WIP hours from unbilled billable time entries
# ---------------------------------------------------------------------------


def test_summary_wip_hours_from_time_entries(
    owner_client_a: httpx.Client, world: SeedWorld
) -> None:
    """Unbilled billable hours on the engagement's projects appear in wip_hours."""
    db = make_service_client()
    eng_id = _seed_engagement(
        db,
        tenant_id=world.tenant_a.tenant_id,
        client_id=world.tenant_a.client_ids[0],
        billing_arrangement="time_and_materials",
        run_id=world.run_id,
    )
    # Create a project under the engagement
    project_res = (
        db.table("projects")
        .insert(
            {
                "tenant_id": world.tenant_a.tenant_id,
                "engagement_id": eng_id,
                "name": f"WIP test project {world.run_id}",
                "status": "active",
                "currency": "USD",
            }
        )
        .execute()
    )
    project_id = project_res.data[0]["id"]
    employee_id = world.tenant_a.employee_ids[0]

    # 3 unbilled billable hours + 2 billed hours (should not count) + 1 non-billable
    te_unbilled_1 = _seed_time_entry(
        db,
        tenant_id=world.tenant_a.tenant_id,
        project_id=project_id,
        employee_id=employee_id,
        hours="1.50",
        billable=True,
        billing_status="unbilled",
    )
    te_unbilled_2 = _seed_time_entry(
        db,
        tenant_id=world.tenant_a.tenant_id,
        project_id=project_id,
        employee_id=employee_id,
        hours="1.50",
        billable=True,
        billing_status="unbilled",
    )
    _seed_time_entry(
        db,
        tenant_id=world.tenant_a.tenant_id,
        project_id=project_id,
        employee_id=employee_id,
        hours="2.00",
        billable=True,
        billing_status="billed",  # already billed — must NOT count
    )
    _seed_time_entry(
        db,
        tenant_id=world.tenant_a.tenant_id,
        project_id=project_id,
        employee_id=employee_id,
        hours="5.00",
        billable=False,       # non-billable — must NOT count
        billing_status="unbilled",
    )

    r = owner_client_a.get(f"/api/v1/engagements/{eng_id}/summary")
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["wip_hours"] == pytest.approx(3.0, rel=1e-3), (
        f"Expected 3.0 WIP hours, got {body['wip_hours']}"
    )
    # wip_value should be a valid money string (value depends on rate; just
    # assert it's parseable and non-negative)
    wip_value = Decimal(body["wip_value"])
    assert wip_value >= Decimal("0"), f"wip_value must be non-negative: {body['wip_value']}"
