"""Unit tests for time entry Pydantic models.

Covers:
  1. hours validation — must be > 0 and <= 24.
  2. hours serialised as string in TimeEntryResponse.
  3. Decimal precision is preserved (not converted to float).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.time_entries import TimeEntryCreate, TimeEntryResponse

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Test 1: hours validation — zero and negative are rejected
# ---------------------------------------------------------------------------


def test_time_entry_create_rejects_zero_hours() -> None:
    """hours must be > 0; zero should raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        TimeEntryCreate(
            project_id="proj-1",
            employee_id="emp-1",
            date="2026-05-01",
            hours=Decimal("0"),
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("hours",) for e in errors)


def test_time_entry_create_rejects_hours_over_24() -> None:
    """hours must be <= 24; 24.01 should raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        TimeEntryCreate(
            project_id="proj-1",
            employee_id="emp-1",
            date="2026-05-01",
            hours=Decimal("24.01"),
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("hours",) for e in errors)


def test_time_entry_create_accepts_boundary_hours() -> None:
    """hours = 24.00 (exactly) should be valid."""
    entry = TimeEntryCreate(
        project_id="proj-1",
        employee_id="emp-1",
        date="2026-05-01",
        hours=Decimal("24.00"),
    )
    assert entry.hours == Decimal("24")


# ---------------------------------------------------------------------------
# Test 2: hours serialised as string in response
# ---------------------------------------------------------------------------


def test_time_entry_response_serialises_hours_as_string() -> None:
    """TimeEntryResponse.hours must be a string, not a Decimal or float."""
    resp = TimeEntryResponse(
        id="entry-1",
        tenant_id="tenant-1",
        project_id="proj-1",
        employee_id="emp-1",
        date="2026-05-01",
        hours=Decimal("7.5"),  # passed as Decimal
        description="Design session",
        billable=True,
        billing_status="unbilled",
        created_at="2026-05-01T09:00:00Z",
    )
    assert isinstance(resp.hours, str)
    assert resp.hours == "7.5"


# ---------------------------------------------------------------------------
# Test 3: Decimal precision preserved — no float rounding
# ---------------------------------------------------------------------------


def test_time_entry_response_preserves_decimal_precision() -> None:
    """Decimal('8.25') must not become '8.2500000000001' via float coercion."""
    resp = TimeEntryResponse(
        id="entry-2",
        tenant_id="tenant-1",
        project_id="proj-1",
        employee_id="emp-1",
        date="2026-05-02",
        hours="8.25",  # passed as string (as it would come from DB)
        description="Implementation",
        billable=True,
        billing_status="unbilled",
        created_at="2026-05-02T10:00:00Z",
    )
    assert resp.hours == "8.25"
    # Ensure it round-trips cleanly to Decimal
    assert Decimal(resp.hours) == Decimal("8.25")
