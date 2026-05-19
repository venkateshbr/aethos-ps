"""Unit tests for Engagement Pydantic models.

Tests cover:
- EngagementResponse serialises total_value as a string (not Decimal)
- All billing_arrangement enum values are accepted
- BillingTerms coerces string/int inputs to Decimal
- EngagementResponse.from_db builds correctly from a DB row dict
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.engagements import (
    BillingTerms,
    EngagementCreate,
    EngagementResponse,
)

# ---------------------------------------------------------------------------
# Serialisation: Decimal → str in JSON responses
# ---------------------------------------------------------------------------


def test_engagement_response_serialises_total_value_as_string() -> None:
    resp = EngagementResponse(
        id="abc",
        tenant_id="t1",
        client_id="c1",
        name="Acme Q1",
        billing_arrangement="time_and_materials",
        currency="USD",
        total_value=Decimal("50000.00"),
        status="draft",
        start_date=None,
        end_date=None,
        created_at="2026-05-19",
    )
    assert resp.total_value == "50000.00"
    assert isinstance(resp.total_value, str)


def test_engagement_response_total_value_none() -> None:
    resp = EngagementResponse(
        id="abc",
        tenant_id="t1",
        client_id="c1",
        name="T&M no value",
        billing_arrangement="time_and_materials",
        currency="USD",
        total_value=None,
        status="draft",
        start_date=None,
        end_date=None,
        created_at="2026-05-19",
    )
    assert resp.total_value is None


# ---------------------------------------------------------------------------
# Billing arrangement enum validation
# ---------------------------------------------------------------------------


def test_billing_arrangement_enum_values() -> None:
    valid = [
        "time_and_materials",
        "fixed_fee",
        "retainer",
        "retainer_draw",
        "milestone",
        "capped_tm",
    ]
    for v in valid:
        eng = EngagementCreate(client_id="c1", name="x", billing_arrangement=v)  # type: ignore[arg-type]
        assert eng.billing_arrangement == v


def test_billing_arrangement_invalid_value_raises() -> None:
    with pytest.raises(ValidationError):
        EngagementCreate(client_id="c1", name="x", billing_arrangement="daily_rate")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# BillingTerms coercion
# ---------------------------------------------------------------------------


def test_billing_terms_coerces_str_to_decimal() -> None:
    terms = BillingTerms(fixed_fee_amount="25000.50")  # type: ignore[arg-type]
    assert terms.fixed_fee_amount == Decimal("25000.50")


def test_billing_terms_coerces_int_to_decimal() -> None:
    terms = BillingTerms(retainer_monthly_amount=5000)  # type: ignore[arg-type]
    assert terms.retainer_monthly_amount == Decimal("5000")


def test_billing_terms_all_none_allowed() -> None:
    terms = BillingTerms()
    assert terms.fixed_fee_amount is None
    assert terms.cap_amount is None


# ---------------------------------------------------------------------------
# EngagementResponse.from_db
# ---------------------------------------------------------------------------


def test_engagement_from_db_with_total_value() -> None:
    row = {
        "id": "eng-123",
        "tenant_id": "tenant-abc",
        "client_id": "client-xyz",
        "name": "Acme Retainer",
        "billing_arrangement": "retainer",
        "currency": "USD",
        "total_value": "12000.00",
        "status": "active",
        "start_date": "2026-01-01",
        "end_date": None,
        "created_at": "2026-05-19T10:00:00+00:00",
    }
    resp = EngagementResponse.from_db(row)
    assert resp.id == "eng-123"
    assert resp.total_value == "12000.00"
    assert isinstance(resp.total_value, str)
    assert resp.billing_terms is None


def test_engagement_from_db_null_total_value() -> None:
    row = {
        "id": "eng-456",
        "tenant_id": "tenant-abc",
        "client_id": "client-xyz",
        "name": "T&M open ended",
        "billing_arrangement": "time_and_materials",
        "currency": "GBP",
        "total_value": None,
        "status": "draft",
        "start_date": None,
        "end_date": None,
        "created_at": "2026-05-19T10:00:00+00:00",
    }
    resp = EngagementResponse.from_db(row)
    assert resp.total_value is None


# ---------------------------------------------------------------------------
# EngagementCreate field constraints
# ---------------------------------------------------------------------------


def test_engagement_create_name_too_short_raises() -> None:
    with pytest.raises(ValidationError):
        EngagementCreate(client_id="c1", name="", billing_arrangement="fixed_fee")  # type: ignore[arg-type]


def test_engagement_create_total_value_coerced_from_string() -> None:
    eng = EngagementCreate(
        client_id="c1",
        name="Test",
        billing_arrangement="fixed_fee",
        total_value="99999.99",  # type: ignore[arg-type]
    )
    assert eng.total_value == Decimal("99999.99")
