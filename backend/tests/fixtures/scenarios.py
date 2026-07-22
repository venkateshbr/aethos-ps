"""Deterministic test scenarios for the Aksha QA regression suite.

Builds two tenants (`Acme` US/USD and `Bravo` UK/GBP) with a deterministic data
set: clients, engagements, projects, time entries, one draft invoice, one bill.
Every test artifact is prefixed with the test-run id so a sweep-clean script can
delete safely.

Design rules
------------
- Service-role client used for seeding (bypasses RLS).
- `app_metadata.role` set per user so JWTs we mint match RBAC expectations.
- All money values are `Decimal` strings to avoid float drift.
- Idempotent: re-running `seed_two_tenants()` returns the existing artifacts
  rather than duplicating rows. This keeps test runs cheap.
"""

from __future__ import annotations

import os
import time as _time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import jwt

from app.services.security_service import LEGACY_ROLE_TO_SECURITY_ROLE
from supabase import Client, create_client

# Stable test-run prefix per process. Lets a single `pytest` run reuse seeded
# tenants across files while still being easy to identify and clean up.
_RUN_ID = os.environ.get("AKSHA_RUN_ID", f"aksha-{uuid.uuid4().hex[:8]}")
TENANT_A_SLUG = f"acme-{_RUN_ID}"
TENANT_B_SLUG = f"bravo-{_RUN_ID}"


def _scenario_user_id(identity: str) -> str:
    """Return a deterministic user UUID within the current fixture run."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"aethos-aksha:{_RUN_ID}:{identity}"))


@dataclass
class SeedUser:
    """A user we mint JWTs for. Not actually created in Supabase Auth — we just
    need a stable uuid + role to bind to a tenant_users row."""

    user_id: str
    email: str
    role: str  # owner / admin / manager / member / viewer


@dataclass
class SeedTenant:
    """Materialised tenant with primary user + a few entities."""

    tenant_id: str
    name: str
    slug: str
    country: str
    base_currency: str
    owner: SeedUser
    members: dict[str, SeedUser] = field(default_factory=dict)
    client_ids: list[str] = field(default_factory=list)
    vendor_ids: list[str] = field(default_factory=list)
    engagement_ids: list[str] = field(default_factory=list)
    project_ids: list[str] = field(default_factory=list)
    employee_ids: list[str] = field(default_factory=list)
    invoice_ids: list[str] = field(default_factory=list)
    bill_ids: list[str] = field(default_factory=list)


@dataclass
class SeedWorld:
    """The two-tenant world fixture handed to tests."""

    run_id: str
    tenant_a: SeedTenant
    tenant_b: SeedTenant


# ---------------------------------------------------------------------------
# Service-role client
# ---------------------------------------------------------------------------


def make_service_client() -> Client:
    """Return a Supabase client authenticated as service-role (bypasses RLS)."""
    url = os.environ.get("SUPABASE_URL") or ""
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing — copy backend/.env "
            "from a worktree that has the real credentials."
        )
    return create_client(url, key)


# ---------------------------------------------------------------------------
# JWT minting (we don't go through Supabase Auth for the test users)
# ---------------------------------------------------------------------------


def mint_jwt(*, user_id: str, email: str, role: str = "owner") -> str:
    """Mint a Supabase-compatible JWT signed with SUPABASE_JWT_SECRET.

    Backend `get_current_user` reads ``sub``, ``email``, and
    ``app_metadata.role``. We populate them here.
    """
    secret = os.environ.get("SUPABASE_JWT_SECRET") or ""
    if not secret:
        raise RuntimeError("SUPABASE_JWT_SECRET missing")
    now = int(_time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
        "iat": now,
        "exp": now + 60 * 60,  # 1h
        "iss": "https://glcljucaayeesvrsjths.supabase.co/auth/v1",
        "app_metadata": {"role": role, "provider": "test"},
        "user_metadata": {},
    }
    return jwt.encode(payload, secret, algorithm="HS256")


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------


def _ensure_tenant(
    db: Client,
    *,
    name: str,
    slug: str,
    country: str,
    currency: str,
) -> str:
    existing = (
        db.table("tenants")
        .select("id")
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]
    tid = str(uuid.uuid4())
    db.table("tenants").insert(
        {
            "id": tid,
            "name": name,
            "slug": slug,
            "country": country,
            "base_currency": currency,
            "plan_tier": "growth",
            "status": "active",
            "stripe_subscription_status": "trialing",
            "trial_ends_at": (datetime.now(UTC) + timedelta(days=14)).isoformat(),
        }
    ).execute()
    return tid


def _ensure_membership(
    db: Client, *, tenant_id: str, user: SeedUser
) -> None:
    existing = (
        db.table("tenant_users")
        .select("id, role")
        .eq("tenant_id", tenant_id)
        .eq("user_id", user.user_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        membership = existing.data[0]
        if str(membership.get("role")) != user.role:
            raise RuntimeError(
                f"Seed membership role mismatch for {user.user_id}: "
                f"expected {user.role!r}, found {membership.get('role')!r}."
            )
    else:
        result = db.table("tenant_users").insert(
            {
                "tenant_id": tenant_id,
                "user_id": user.user_id,
                "role": user.role,
                "joined_at": datetime.now(UTC).isoformat(),
            }
        ).execute()
        membership = result.data[0]

    tenant_user_id = str(membership["id"])
    security_role_code = LEGACY_ROLE_TO_SECURITY_ROLE.get(user.role)
    if security_role_code is None:
        raise RuntimeError(f"No canonical security role mapping for {user.role!r}.")

    roles = (
        db.table("security_roles")
        .select("id")
        .eq("code", security_role_code)
        .is_("tenant_id", "null")
        .is_("deleted_at", "null")
        .limit(1)
        .execute()
    )
    if not roles.data:
        raise RuntimeError(
            f"System security role {security_role_code!r} is missing; "
            "apply migration 0096 before seeding real-stack scenarios."
        )
    security_role_id = str(roles.data[0]["id"])

    assignments = (
        db.table("tenant_user_roles")
        .select("id, security_role_id")
        .eq("tenant_id", tenant_id)
        .eq("tenant_user_id", tenant_user_id)
        .is_("deleted_at", "null")
        .execute()
    )
    unexpected_role_ids = sorted(
        str(row["security_role_id"])
        for row in assignments.data
        if str(row["security_role_id"]) != security_role_id
    )
    if unexpected_role_ids:
        raise RuntimeError(
            f"Seed membership {tenant_user_id} has an unexpected active security role; "
            "refusing to create an over-privileged fixture."
        )
    if assignments.data:
        return
    db.table("tenant_user_roles").insert(
        {
            "tenant_id": tenant_id,
            "tenant_user_id": tenant_user_id,
            "security_role_id": security_role_id,
        }
    ).execute()


def _ensure_client(
    db: Client,
    *,
    tenant_id: str,
    name: str,
    kind: str = "customer",
    currency: str = "USD",
    email: str = "ap@example.com",
) -> str:
    existing = (
        db.table("clients")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("name", name)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]
    res = (
        db.table("clients")
        .insert(
            {
                "tenant_id": tenant_id,
                "name": name,
                "kind": kind,
                "currency": currency,
                "billing_email": email,
                "payment_terms_days": 30,
            }
        )
        .execute()
    )
    return res.data[0]["id"]


def _ensure_engagement(
    db: Client,
    *,
    tenant_id: str,
    client_id: str,
    name: str,
    currency: str = "USD",
    billing_arrangement: str = "time_and_materials",
) -> str:
    """Create an engagement and its 1:1 billing_terms row (idempotent on name)."""
    existing = (
        db.table("engagements")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("name", name)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]
    res = (
        db.table("engagements")
        .insert(
            {
                "tenant_id": tenant_id,
                "client_id": client_id,
                "name": name,
                "billing_arrangement": billing_arrangement,
                "status": "active",
                "start_date": (datetime.now(UTC) - timedelta(days=30)).date().isoformat(),
                "currency": currency,
                "total_value": "100000.00",
            }
        )
        .execute()
    )
    eng_id = res.data[0]["id"]
    # 1:1 billing_terms row
    try:
        db.table("engagement_billing_terms").insert(
            {
                "engagement_id": eng_id,
                "tenant_id": tenant_id,
                "fixed_fee_amount": (
                    "100000.00" if billing_arrangement in ("fixed_fee", "capped_tm") else None
                ),
                "cap_amount": (
                    "120000.00" if billing_arrangement == "capped_tm" else None
                ),
                "retainer_monthly_amount": (
                    "10000.00" if billing_arrangement in ("retainer", "retainer_draw") else None
                ),
            }
        ).execute()
    except Exception:
        # Some test environments may have already inserted by trigger; ignore.
        pass
    return eng_id


def _ensure_project(
    db: Client,
    *,
    tenant_id: str,
    engagement_id: str,
    name: str,
    currency: str = "USD",
) -> str:
    existing = (
        db.table("projects")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("name", name)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]
    res = (
        db.table("projects")
        .insert(
            {
                "tenant_id": tenant_id,
                "engagement_id": engagement_id,
                "name": name,
                "status": "active",
                "currency": currency,
                "budget_hours": "400.00",
                "budget": "60000.00",
            }
        )
        .execute()
    )
    return res.data[0]["id"]


def _ensure_employee(
    db: Client,
    *,
    tenant_id: str,
    first_name: str,
    last_name: str,
    email: str,
    bill_rate: str,
    currency: str,
) -> str:
    """Seed an employee row for time-entry tests. Idempotent on email."""
    existing = (
        db.table("employees")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("email", email)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]
    res = (
        db.table("employees")
        .insert(
            {
                "tenant_id": tenant_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "employment_type": "full_time",
                "default_bill_rate": bill_rate,
                "default_bill_rate_currency": currency,
                "cost_rate": "100.00",
                "available_hours_per_week": "40.00",
                "status": "active",
            }
        )
        .execute()
    )
    return res.data[0]["id"]


def _seed_tenant(
    db: Client,
    *,
    name: str,
    slug: str,
    country: str,
    currency: str,
    owner: SeedUser,
    extra_members: list[SeedUser],
) -> SeedTenant:
    tid = _ensure_tenant(db, name=name, slug=slug, country=country, currency=currency)
    _ensure_membership(db, tenant_id=tid, user=owner)
    members: dict[str, SeedUser] = {}
    for m in extra_members:
        _ensure_membership(db, tenant_id=tid, user=m)
        members[m.role] = m

    customer = _ensure_client(
        db,
        tenant_id=tid,
        name=f"Customer Co {slug[-6:]}",
        kind="customer",
        currency=currency,
        email=f"ap@customer-{slug[-6:]}.example.com",
    )
    vendor = _ensure_client(
        db,
        tenant_id=tid,
        name=f"Vendor Co {slug[-6:]}",
        kind="vendor",
        currency=currency,
        email=f"billing@vendor-{slug[-6:]}.example.com",
    )
    engagement = _ensure_engagement(
        db,
        tenant_id=tid,
        client_id=customer,
        name=f"Discovery Engagement {slug[-6:]}",
        currency=currency,
        billing_arrangement="time_and_materials",
    )
    project = _ensure_project(
        db,
        tenant_id=tid,
        engagement_id=engagement,
        name=f"Phase 1 — Discovery {slug[-6:]}",
        currency=currency,
    )
    employee = _ensure_employee(
        db,
        tenant_id=tid,
        first_name="Alice",
        last_name=f"Tester{slug[-6:]}",
        email=f"alice-employee-{slug[-6:]}@aksha.test",
        bill_rate="200.00",
        currency=currency,
    )

    return SeedTenant(
        tenant_id=tid,
        name=name,
        slug=slug,
        country=country,
        base_currency=currency,
        owner=owner,
        members=members,
        client_ids=[customer],
        vendor_ids=[vendor],
        engagement_ids=[engagement],
        project_ids=[project],
        employee_ids=[employee],
    )


def seed_two_tenants() -> SeedWorld:
    """Idempotently build two isolated tenants and return the world handle."""
    db = make_service_client()

    a_owner = SeedUser(
        user_id=_scenario_user_id("tenant-a-owner"),
        email=f"alice-owner+{_RUN_ID}@aksha.test",
        role="owner",
    )
    a_manager = SeedUser(
        user_id=_scenario_user_id("tenant-a-manager"),
        email=f"mary-manager+{_RUN_ID}@aksha.test",
        role="manager",
    )
    a_viewer = SeedUser(
        user_id=_scenario_user_id("tenant-a-viewer"),
        email=f"vivian-viewer+{_RUN_ID}@aksha.test",
        role="viewer",
    )

    b_owner = SeedUser(
        user_id=_scenario_user_id("tenant-b-owner"),
        email=f"bob-owner+{_RUN_ID}@aksha.test",
        role="owner",
    )

    tenant_a = _seed_tenant(
        db,
        name=f"Acme Consulting {_RUN_ID}",
        slug=TENANT_A_SLUG,
        country="US",
        currency="USD",
        owner=a_owner,
        extra_members=[a_manager, a_viewer],
    )
    tenant_b = _seed_tenant(
        db,
        name=f"Bravo Advisory {_RUN_ID}",
        slug=TENANT_B_SLUG,
        country="GB",
        currency="GBP",
        owner=b_owner,
        extra_members=[],
    )

    return SeedWorld(run_id=_RUN_ID, tenant_a=tenant_a, tenant_b=tenant_b)


# ---------------------------------------------------------------------------
# Cleanup (verified soft-delete — invoked from session-end hook)
# ---------------------------------------------------------------------------


def sweep_clean(world: SeedWorld) -> None:
    """Soft-delete both seeded tenants and verify neither remains active.

    A hard tenant delete is not a valid cleanup primitive: accounting and
    commercial foreign keys deliberately use ``RESTRICT``/``NO ACTION`` and
    can block the cascade. The production tenant-delete endpoint likewise uses
    ``status='deleted'``. Cleanup attempts both tenants, then raises one safe
    aggregate error instead of hiding a partial failure during pytest teardown.
    """
    db = make_service_client()
    failures: list[tuple[str, str]] = []

    for tenant in (world.tenant_a, world.tenant_b):
        slug = tenant.slug
        if not slug.endswith(f"-{world.run_id}"):
            failures.append((slug, "unsafe_slug"))
            continue
        try:
            (
                db.table("tenants")
                .update(
                    {
                        "status": "deleted",
                        "stripe_subscription_status": "canceled",
                    }
                )
                .eq("id", tenant.tenant_id)
                .eq("slug", slug)
                .execute()
            )
            verification = (
                db.table("tenants")
                .select("id,status")
                .eq("id", tenant.tenant_id)
                .eq("slug", slug)
                .limit(1)
                .execute()
            )
            if verification.data and verification.data[0].get("status") != "deleted":
                raise RuntimeError("cleanup_verification_failed")
        except Exception as exc:
            # Do not include backend error text: it can contain infrastructure
            # details. The exception type plus safe fixture slug is actionable.
            failures.append((slug, type(exc).__name__))

    if failures:
        summary = ", ".join(f"{slug} ({error_type})" for slug, error_type in failures)
        raise RuntimeError(
            f"Aksha fixture cleanup failed for {summary}. "
            "One or more test tenants may remain active."
        )


# ---------------------------------------------------------------------------
# Helpers for tests
# ---------------------------------------------------------------------------


def auth_headers(seed: SeedTenant, *, role: str = "owner") -> dict[str, str]:
    """Return ``{Authorization, X-Tenant-ID}`` headers for a tenant.

    ``role='owner'`` uses the seeded owner; otherwise looks up the member by
    role.
    """
    if role == "owner":
        user = seed.owner
    else:
        user = seed.members.get(role)
        if user is None:
            raise KeyError(f"No seeded member with role={role!r} for tenant {seed.slug}")
    token = mint_jwt(user_id=user.user_id, email=user.email, role=role)
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": seed.tenant_id,
    }


def decimal_str(value: str | Decimal | int | float) -> str:
    """Render a money value as a Decimal-safe string."""
    return str(Decimal(str(value)).quantize(Decimal("0.01")))


__all__ = [
    "SeedTenant",
    "SeedUser",
    "SeedWorld",
    "auth_headers",
    "decimal_str",
    "make_service_client",
    "mint_jwt",
    "seed_two_tenants",
    "sweep_clean",
]
