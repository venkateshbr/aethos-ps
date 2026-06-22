"""Manual Journal Entry API tests — POST /api/v1/accounting/journal-entries.

Covers:
  - Balanced DR/CR pair posts successfully (201, entry_number returned)
  - Unbalanced journal (DR 1000 / CR 900) rejected (422)
  - Entry date in a locked period rejected (422, code=period_locked)
  - Unknown account_id rejected (422)
  - Staff/viewer role → 403
  - Manager role → 201

All tests require the real stack (Supabase + running API).
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import httpx
import pytest

from tests.fixtures.scenarios import SeedWorld, make_service_client, mint_jwt

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_accounting,
    pytest.mark.requires_supabase,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_tenant_accounts(tenant_id: str) -> list[dict]:
    """Return up to 2 accounts from the tenant's COA (seeded by onboarding trigger)."""
    db = make_service_client()
    result = (
        db.table("accounts")
        .select("id, code, name")
        .eq("tenant_id", tenant_id)
        .limit(10)
        .execute()
    )
    return result.data or []


def _balanced_payload(dr_account_id: str, cr_account_id: str, *, date: str = "2099-01-15") -> dict:
    return {
        "description": "Month-end accrual — test entry",
        "entry_date": date,
        "reference": "TEST-REF-001",
        "lines": [
            {
                "direction": "DR",
                "account_id": dr_account_id,
                "amount": "1000.00",
                "currency": "USD",
                "description": "Debit leg",
            },
            {
                "direction": "CR",
                "account_id": cr_account_id,
                "amount": "1000.00",
                "currency": "USD",
                "description": "Credit leg",
            },
        ],
    }


def _cleanup_journal(je_id: str | None, tenant_id: str) -> None:
    """Delete a journal entry row inserted during a test (best-effort)."""
    if not je_id:
        return
    try:
        db = make_service_client()
        db.table("journal_entries").delete().eq("id", je_id).eq("tenant_id", tenant_id).execute()
    except Exception:
        pass


def _lock_period(tenant_id: str, period: str, user_id: str) -> None:
    from datetime import UTC, datetime

    db = make_service_client()
    # Idempotent — ignore if already locked
    existing = (
        db.table("period_locks")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("period", period)
        .execute()
    )
    if not existing.data:
        db.table("period_locks").insert(
            {
                "tenant_id": tenant_id,
                "period": period,
                "locked_at": datetime.now(UTC).isoformat(),
                "locked_by": user_id,
            }
        ).execute()


def _unlock_period(tenant_id: str, period: str) -> None:
    try:
        db = make_service_client()
        db.table("period_locks").delete().eq("tenant_id", tenant_id).eq("period", period).execute()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def owner_client(api_base_url: str, world: SeedWorld) -> httpx.Client:
    """Owner-role client for tenant A."""
    token = mint_jwt(
        user_id=world.tenant_a.owner.user_id,
        email=world.tenant_a.owner.email,
        role="owner",
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": world.tenant_a.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        yield c


@pytest.fixture
def manager_client(api_base_url: str, world: SeedWorld) -> httpx.Client:
    """Manager-role client for tenant A."""
    member = world.tenant_a.members.get("manager")
    assert member is not None, "No manager member seeded for tenant A"
    token = mint_jwt(user_id=member.user_id, email=member.email, role="manager")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": world.tenant_a.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        yield c


@pytest.fixture
def viewer_client(api_base_url: str, world: SeedWorld) -> httpx.Client:
    """Viewer-role client for tenant A."""
    member = world.tenant_a.members.get("viewer")
    assert member is not None, "No viewer member seeded for tenant A"
    token = mint_jwt(user_id=member.user_id, email=member.email, role="viewer")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": world.tenant_a.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        yield c


@pytest.fixture
def tenant_accounts(world: SeedWorld) -> list[dict]:
    """Two COA accounts from tenant A; skip if fewer than 2 are seeded."""
    accts = _get_tenant_accounts(world.tenant_a.tenant_id)
    if len(accts) < 2:
        pytest.skip("Tenant A has fewer than 2 COA accounts — onboarding seed missing")
    return accts


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_balanced_journal_posts(
    owner_client: httpx.Client,
    world: SeedWorld,
    tenant_accounts: list[dict],
) -> None:
    """A balanced DR/CR journal entry posts successfully, returns 201 + entry_number."""
    dr_id = tenant_accounts[0]["id"]
    cr_id = tenant_accounts[1]["id"]
    payload = _balanced_payload(dr_id, cr_id)

    r = owner_client.post("/api/v1/accounting/journal-entries", json=payload)

    assert r.status_code == 201, r.text
    body = r.json()
    assert "id" in body
    assert "entry_number" in body
    assert body["entry_number"].startswith("JE-")
    assert body["reference_type"] == "manual"
    assert "lines" in body
    assert len(body["lines"]) >= 2

    _cleanup_journal(body.get("id"), world.tenant_a.tenant_id)


def test_unbalanced_journal_rejected(
    owner_client: httpx.Client,
    tenant_accounts: list[dict],
) -> None:
    """DR 1000 / CR 900 (imbalanced by > 0.01) must be rejected with 422."""
    dr_id = tenant_accounts[0]["id"]
    cr_id = tenant_accounts[1]["id"]
    payload = {
        "description": "Imbalanced test entry",
        "entry_date": "2099-01-15",
        "lines": [
            {
                "direction": "DR",
                "account_id": dr_id,
                "amount": "1000.00",
                "currency": "USD",
            },
            {
                "direction": "CR",
                "account_id": cr_id,
                "amount": "900.00",  # off by 100 — way over tolerance
                "currency": "USD",
            },
        ],
    }

    r = owner_client.post("/api/v1/accounting/journal-entries", json=payload)

    assert r.status_code == 422, (
        f"Expected 422 for imbalanced journal, got {r.status_code}: {r.text}"
    )
    detail = r.json().get("detail", "")
    assert "imbalanced" in str(detail).lower() or "balance" in str(detail).lower(), (
        f"Expected error mentioning balance, got: {detail}"
    )


def test_locked_period_rejected(
    owner_client: httpx.Client,
    world: SeedWorld,
    tenant_accounts: list[dict],
) -> None:
    """Entry date in a locked period must be rejected with 422 and code=period_locked."""
    locked_period = "2087-06"
    entry_date = "2087-06-15"
    _lock_period(world.tenant_a.tenant_id, locked_period, world.tenant_a.owner.user_id)

    try:
        dr_id = tenant_accounts[0]["id"]
        cr_id = tenant_accounts[1]["id"]
        payload = _balanced_payload(dr_id, cr_id, date=entry_date)

        r = owner_client.post("/api/v1/accounting/journal-entries", json=payload)

        assert r.status_code == 422, (
            f"Expected 422 for locked period, got {r.status_code}: {r.text}"
        )
        detail = r.json().get("detail", {})
        # Detail may be a dict with code, or a string mentioning "locked"
        detail_str = str(detail).lower()
        assert "locked" in detail_str or "period_locked" in detail_str, (
            f"Expected period_locked error, got: {detail}"
        )
    finally:
        _unlock_period(world.tenant_a.tenant_id, locked_period)


def test_invalid_account_rejected(
    owner_client: httpx.Client,
    tenant_accounts: list[dict],
) -> None:
    """An unknown account_id (not in the tenant's COA) must be rejected with 422."""
    valid_id = tenant_accounts[0]["id"]
    unknown_id = str(uuid.uuid4())  # guaranteed to not exist

    payload = {
        "description": "Unknown account test",
        "entry_date": "2099-02-10",
        "lines": [
            {
                "direction": "DR",
                "account_id": unknown_id,
                "amount": "500.00",
                "currency": "USD",
            },
            {
                "direction": "CR",
                "account_id": valid_id,
                "amount": "500.00",
                "currency": "USD",
            },
        ],
    }

    r = owner_client.post("/api/v1/accounting/journal-entries", json=payload)

    assert r.status_code == 422, (
        f"Expected 422 for unknown account, got {r.status_code}: {r.text}"
    )
    detail = str(r.json().get("detail", "")).lower()
    assert "account" in detail or "unknown" in detail, (
        f"Expected account-related error, got: {detail}"
    )


def test_viewer_role_forbidden(
    viewer_client: httpx.Client,
    tenant_accounts: list[dict],
) -> None:
    """Viewer role must be rejected with 403 — journal entry is manager+ only."""
    dr_id = tenant_accounts[0]["id"]
    cr_id = tenant_accounts[1]["id"]
    payload = _balanced_payload(dr_id, cr_id)

    r = viewer_client.post("/api/v1/accounting/journal-entries", json=payload)

    assert r.status_code == 403, (
        f"RBAC GAP: viewer was allowed to post a manual journal (status {r.status_code}). "
        f"Body: {r.text[:200]}"
    )


def test_manager_role_allowed(
    manager_client: httpx.Client,
    world: SeedWorld,
    tenant_accounts: list[dict],
) -> None:
    """Manager role must be allowed to post a manual journal entry → 201."""
    dr_id = tenant_accounts[0]["id"]
    cr_id = tenant_accounts[1]["id"]
    payload = _balanced_payload(dr_id, cr_id)

    r = manager_client.post("/api/v1/accounting/journal-entries", json=payload)

    assert r.status_code == 201, (
        f"Manager should be allowed to post manual journals, got {r.status_code}: {r.text}"
    )
    body = r.json()
    assert "entry_number" in body

    _cleanup_journal(body.get("id"), world.tenant_a.tenant_id)


def test_list_journal_entries(
    owner_client: httpx.Client,
    world: SeedWorld,
    tenant_accounts: list[dict],
) -> None:
    """GET /api/v1/accounting/journal-entries returns a list for the tenant."""
    # First post one entry so the list is non-empty
    dr_id = tenant_accounts[0]["id"]
    cr_id = tenant_accounts[1]["id"]
    payload = _balanced_payload(dr_id, cr_id)
    post_r = owner_client.post("/api/v1/accounting/journal-entries", json=payload)
    assert post_r.status_code == 201, post_r.text
    je_id = post_r.json().get("id")

    try:
        r = owner_client.get("/api/v1/accounting/journal-entries")
        assert r.status_code == 200, r.text
        body = r.json()
        assert isinstance(body, list), f"Expected list, got: {type(body)}"
        # Should contain at least the entry we just posted
        ids = [item.get("id") for item in body]
        assert je_id in ids, f"Newly posted entry {je_id} not found in list"
    finally:
        _cleanup_journal(je_id, world.tenant_a.tenant_id)


def test_list_journal_entries_reference_type_filter(
    owner_client: httpx.Client,
    world: SeedWorld,
    tenant_accounts: list[dict],
) -> None:
    """GET /journal-entries?reference_type=manual returns only manual entries."""
    dr_id = tenant_accounts[0]["id"]
    cr_id = tenant_accounts[1]["id"]
    payload = _balanced_payload(dr_id, cr_id)
    post_r = owner_client.post("/api/v1/accounting/journal-entries", json=payload)
    assert post_r.status_code == 201, post_r.text
    je_id = post_r.json().get("id")

    try:
        r = owner_client.get("/api/v1/accounting/journal-entries?reference_type=manual")
        assert r.status_code == 200, r.text
        body = r.json()
        assert isinstance(body, list)
        for item in body:
            assert item.get("reference_type") == "manual", (
                f"Filter failed — non-manual entry in result: {item}"
            )
    finally:
        _cleanup_journal(je_id, world.tenant_a.tenant_id)


def test_single_line_rejected(
    owner_client: httpx.Client,
    tenant_accounts: list[dict],
) -> None:
    """A journal with only one line must be rejected with 422 (min 2 lines)."""
    dr_id = tenant_accounts[0]["id"]
    payload = {
        "description": "Single line test",
        "entry_date": "2099-03-01",
        "lines": [
            {
                "direction": "DR",
                "account_id": dr_id,
                "amount": "100.00",
                "currency": "USD",
            }
        ],
    }

    r = owner_client.post("/api/v1/accounting/journal-entries", json=payload)
    assert r.status_code == 422, (
        f"Expected 422 for single-line journal, got {r.status_code}: {r.text}"
    )


def test_negative_amount_rejected(
    owner_client: httpx.Client,
    tenant_accounts: list[dict],
) -> None:
    """Amount must be positive; negative values must fail Pydantic validation (422)."""
    dr_id = tenant_accounts[0]["id"]
    cr_id = tenant_accounts[1]["id"]
    payload = {
        "description": "Negative amount test",
        "entry_date": "2099-03-01",
        "lines": [
            {
                "direction": "DR",
                "account_id": dr_id,
                "amount": "-100.00",
                "currency": "USD",
            },
            {
                "direction": "CR",
                "account_id": cr_id,
                "amount": "-100.00",
                "currency": "USD",
            },
        ],
    }

    r = owner_client.post("/api/v1/accounting/journal-entries", json=payload)
    assert r.status_code == 422, (
        f"Expected 422 for negative amount, got {r.status_code}: {r.text}"
    )
