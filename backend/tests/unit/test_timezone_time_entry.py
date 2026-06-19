"""Unit tests for timezone-aware time entries (#190).

Tests that:
- TimeEntryCreate accepts a timezone field (default UTC)
- TimeEntryResponse includes the timezone field
- The service includes timezone in the DB insert payload
- The response correctly reflects the stored timezone
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Test 1: TimeEntryCreate accepts timezone field and defaults to UTC
# ---------------------------------------------------------------------------


def test_time_entry_create_timezone_defaults_to_utc() -> None:
    """TimeEntryCreate.timezone defaults to 'UTC' when not provided."""
    from datetime import date

    from app.models.time_entries import TimeEntryCreate

    entry = TimeEntryCreate(
        project_id="proj-1",
        employee_id="emp-1",
        date=date(2026, 6, 15),
        hours=Decimal("8"),
    )
    assert entry.timezone == "UTC"


def test_time_entry_create_accepts_custom_timezone() -> None:
    """TimeEntryCreate accepts a valid IANA timezone string."""
    from datetime import date

    from app.models.time_entries import TimeEntryCreate

    entry = TimeEntryCreate(
        project_id="proj-1",
        employee_id="emp-1",
        date=date(2026, 6, 15),
        hours=Decimal("8"),
        timezone="America/New_York",
    )
    assert entry.timezone == "America/New_York"


# ---------------------------------------------------------------------------
# Test 2: TimeEntryResponse includes timezone field
# ---------------------------------------------------------------------------


def test_time_entry_response_includes_timezone() -> None:
    """TimeEntryResponse must include a timezone field."""
    from app.models.time_entries import TimeEntryResponse

    row = {
        "id": "te-001",
        "tenant_id": "tenant-001",
        "project_id": "proj-001",
        "employee_id": "emp-001",
        "date": "2026-06-15",
        "hours": "8.00",
        "description": "Backend work",
        "billable": True,
        "billing_status": "unbilled",
        "status": "approved",
        "timezone": "America/New_York",
        "phase_id": None,
        "created_at": "2026-06-15T10:00:00+00:00",
        "updated_at": "2026-06-15T10:00:00+00:00",
    }

    response = TimeEntryResponse(
        id=row["id"],
        tenant_id=row["tenant_id"],
        project_id=row["project_id"],
        employee_id=row["employee_id"],
        date=row["date"],
        hours=row["hours"],
        description=row["description"],
        billable=row["billable"],
        billing_status=row["billing_status"],
        status=row["status"],
        timezone=row["timezone"],
        phase_id=row["phase_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
    assert response.timezone == "America/New_York"


def test_time_entry_response_timezone_defaults_to_utc() -> None:
    """TimeEntryResponse.timezone defaults to UTC when not provided."""
    from app.models.time_entries import TimeEntryResponse

    response = TimeEntryResponse(
        id="te-001",
        tenant_id="tenant-001",
        project_id="proj-001",
        employee_id="emp-001",
        date="2026-06-15",
        hours="8.00",
        description="",
        billable=True,
        billing_status="unbilled",
        status="approved",
        created_at="2026-06-15T10:00:00+00:00",
        updated_at="2026-06-15T10:00:00+00:00",
    )
    assert response.timezone == "UTC"


# ---------------------------------------------------------------------------
# Test 3: service includes timezone in the DB insert payload
# ---------------------------------------------------------------------------


def test_time_entries_service_creates_entry_with_timezone() -> None:
    """create_entry includes 'timezone' in the repository insert payload."""
    from datetime import date

    from app.models.time_entries import TimeEntryCreate
    from app.services.time_entries_service import TimeEntriesService

    mock_db = MagicMock()
    tenant_id = "tenant-001"

    # Mock period lock — passes
    # Mock project belongs to tenant — True
    # Mock employee belongs to tenant — True
    returned_row = {
        "id": "te-new",
        "tenant_id": tenant_id,
        "project_id": "proj-001",
        "employee_id": "emp-001",
        "date": "2026-06-15",
        "hours": "8.00",
        "description": "",
        "billable": True,
        "billing_status": "unbilled",
        "status": "approved",
        "timezone": "America/New_York",
        "phase_id": None,
        "created_at": "2026-06-15T10:00:00+00:00",
        "updated_at": None,
        "deleted_at": None,
    }

    # Mock the repo calls
    mock_repo = MagicMock()
    mock_repo.project_belongs_to_tenant = AsyncMock(return_value=True)
    mock_repo.employee_belongs_to_tenant = AsyncMock(return_value=True)
    mock_repo.create = AsyncMock(return_value=returned_row)

    # Mock period lock
    import unittest.mock as um

    svc = TimeEntriesService(mock_db, tenant_id)
    svc._repo = mock_repo

    data = TimeEntryCreate(
        project_id="proj-001",
        employee_id="emp-001",
        date=date(2026, 6, 15),
        hours=Decimal("8"),
        timezone="America/New_York",
    )

    async def _run() -> object:
        with um.patch(
            "app.services.time_entries_service.assert_period_open",
            new=AsyncMock(return_value=None),
        ):
            return await svc.create_entry(data, approved_by="user-001")

    result = asyncio.run(_run())

    # Verify timezone was included in the create call payload
    call_args = mock_repo.create.call_args[0][0]
    assert "timezone" in call_args
    assert call_args["timezone"] == "America/New_York"

    # And the response includes the timezone
    assert result.timezone == "America/New_York"


# ---------------------------------------------------------------------------
# Test 4: _row_to_response carries timezone from DB row
# ---------------------------------------------------------------------------


def test_row_to_response_carries_timezone() -> None:
    """_row_to_response maps timezone from the DB row to TimeEntryResponse."""
    from app.services.time_entries_service import _row_to_response

    row = {
        "id": "te-001",
        "tenant_id": "tenant-001",
        "project_id": "proj-001",
        "employee_id": "emp-001",
        "date": "2026-06-15",
        "hours": "8.00",
        "description": "Work",
        "billable": True,
        "billing_status": "unbilled",
        "status": "approved",
        "timezone": "Asia/Singapore",
        "phase_id": None,
        "created_at": "2026-06-15T10:00:00+00:00",
        "updated_at": None,
    }
    response = _row_to_response(row)
    assert response.timezone == "Asia/Singapore"
