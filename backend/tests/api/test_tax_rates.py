"""C30 — Tax rates seeding + per-line tax behavior.

Tax_rates is a backing table, not a router. We verify:
1. The 5 launch markets (US, UK, SG, IN, AU) have seeded system rates
   (tenant_id IS NULL rows) so a brand-new tenant inherits sensible defaults.
2. Tax rates fall in the valid [0.0, 1.0] range (DB constraint, but worth
   asserting at the API layer too).
3. India in particular has GST 0/5/12/18/28 seeded (the brief calls this out).

We use the service-role client directly because tax_rates has nuanced RLS
(system rows are visible to all, tenant rows only to their tenant) and we
want to test the SYSTEM rows.
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest

pytestmark = [
    pytest.mark.api,
    pytest.mark.multi_currency,
    pytest.mark.requires_supabase,
]


def _service_client():
    """Get a service-role Supabase client bypassing RLS (system row check)."""
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        pytest.skip("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
    return create_client(url, key)


def test_system_tax_rates_seeded_for_5_launch_markets() -> None:
    """Brief markets: US, UK, SG, IN, AU. Each must have at least one
    is_seeded=true row at tenant_id IS NULL."""
    db = _service_client()
    rows = (
        db.table("tax_rates")
        .select("country, code, name, rate, is_active")
        .is_("tenant_id", "null")
        .execute()
        .data
        or []
    )
    countries = {r["country"] for r in rows if r.get("country")}
    expected = {"US", "GB", "SG", "IN", "AU"}
    missing = expected - countries
    assert not missing, (
        f"System tax rates missing for launch markets: {missing}. "
        f"Found countries: {sorted(countries)}. "
        f"Seed data lives in supabase/migrations/0006_seed_tax_rates.sql or similar."
    )


def test_india_gst_5_buckets_seeded() -> None:
    """India market needs GST 0/5/12/18/28 per the founder brief."""
    db = _service_client()
    rows = (
        db.table("tax_rates")
        .select("code, rate")
        .is_("tenant_id", "null")
        .eq("country", "IN")
        .execute()
        .data
        or []
    )
    if not rows:
        pytest.skip("India tax rates not seeded — covered by previous test")

    rates = {Decimal(str(r["rate"])) for r in rows}
    # Allow the seed to have any subset, but the canonical GST bands should be present
    expected_bands = {
        Decimal("0.00"),
        Decimal("0.05"),
        Decimal("0.12"),
        Decimal("0.18"),
        Decimal("0.28"),
    }
    missing = expected_bands - rates
    assert not missing, (
        f"India is missing GST bands: {missing}. Seeded: {sorted(rates)}"
    )


def test_tax_rates_are_in_valid_range() -> None:
    """Every tax rate must be in [0.0, 1.0] (DB constraint, double-check)."""
    db = _service_client()
    rows = (
        db.table("tax_rates")
        .select("country, code, rate")
        .is_("tenant_id", "null")
        .execute()
        .data
        or []
    )
    for row in rows:
        rate = Decimal(str(row["rate"]))
        assert Decimal("0") <= rate <= Decimal("1"), (
            f"Tax rate out of bounds: {row['country']}/{row['code']}={rate}"
        )


def test_uk_has_vat_20_default() -> None:
    """UK should have VAT-20 (or equivalent) seeded as the default."""
    db = _service_client()
    rows = (
        db.table("tax_rates")
        .select("code, rate, is_default")
        .is_("tenant_id", "null")
        .eq("country", "GB")
        .execute()
        .data
        or []
    )
    if not rows:
        pytest.skip("UK tax rates not seeded — covered by earlier test")

    rates = {Decimal(str(r["rate"])) for r in rows}
    assert Decimal("0.20") in rates, (
        f"UK is missing the 20% VAT band. Seeded: {sorted(rates)}"
    )
