"""Unit tests for timesheet portal Pydantic models (issue #134)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.timesheet import (
    ApproveRequest,
    TimesheetEntryCreate,
    TimesheetEntryResponse,
)

pytestmark = pytest.mark.unit


def test_entry_create_rejects_zero_hours() -> None:
    with pytest.raises(ValidationError):
        TimesheetEntryCreate(project_id="p1", date="2026-05-01", hours=Decimal("0"))


def test_entry_create_rejects_over_24() -> None:
    with pytest.raises(ValidationError):
        TimesheetEntryCreate(project_id="p1", date="2026-05-01", hours=Decimal("24.5"))


def test_entry_response_serialises_hours_string() -> None:
    r = TimesheetEntryResponse(
        id="x", tenant_id="t", project_id="p", employee_id="e",
        date="2026-05-01", hours=Decimal("4.5"), description="", billable=True,
        status="draft", billing_status="unbilled", created_at="2026-05-01",
    )
    assert r.hours == "4.5"
    assert r.status == "draft"


def test_approve_request_requires_at_least_one_id() -> None:
    with pytest.raises(ValidationError):
        ApproveRequest(entry_ids=[])
