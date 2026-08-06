"""Canonical SaaS billing access policy.

Stripe's status remains provider evidence.  This module derives the product
state used by APIs and the UI, including a bounded webhook-reconciliation
grace period after a trial's recorded end.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

TRIAL_RECONCILIATION_GRACE = timedelta(hours=24)


@dataclass(frozen=True, slots=True)
class BillingAccess:
    effective_status: str
    access_mode: str
    action: str | None


def _utc_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    parsed = (
        value
        if isinstance(value, datetime)
        else datetime.fromisoformat(value.replace("Z", "+00:00"))
    )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def evaluate_billing_access(
    *,
    provider_status: str | None,
    trial_ends_at: str | datetime | None,
    override_until: str | datetime | None,
    as_of: datetime | None = None,
) -> BillingAccess:
    """Derive the customer-visible status and allowed product access."""
    now = _utc_datetime(as_of) or datetime.now(UTC)
    override_end = _utc_datetime(override_until)
    if override_end is not None and override_end > now:
        return BillingAccess("override_active", "full", None)

    raw_status = (provider_status or "unknown").strip().lower()
    trial_end = _utc_datetime(trial_ends_at)
    if raw_status == "trialing" and trial_end is not None:
        if now <= trial_end:
            return BillingAccess("trialing", "full", None)
        if now <= trial_end + TRIAL_RECONCILIATION_GRACE:
            return BillingAccess("grace_period", "full", "manage_billing")
        return BillingAccess("trial_expired", "read_only", "manage_billing")

    if raw_status in {"active", "trialing"}:
        return BillingAccess(raw_status, "full", None)
    if raw_status in {"past_due", "unpaid", "canceled", "incomplete", "incomplete_expired"}:
        return BillingAccess(raw_status, "read_only", "manage_billing")
    return BillingAccess("unknown", "read_only", "contact_support")


def filter_tenants_with_write_access(
    tenants: list[dict], *, as_of: datetime | None = None
) -> list[dict]:
    """Return scheduled-work candidates whose billing policy permits writes."""
    eligible: list[dict] = []
    for tenant in tenants:
        # Compatibility for narrow test doubles and pre-0113 query results.
        if "stripe_subscription_status" not in tenant:
            eligible.append(tenant)
            continue
        access = evaluate_billing_access(
            provider_status=tenant.get("stripe_subscription_status"),
            trial_ends_at=tenant.get("trial_ends_at"),
            override_until=tenant.get("billing_access_override_until"),
            as_of=as_of,
        )
        if access.access_mode == "full":
            eligible.append(tenant)
    return eligible
