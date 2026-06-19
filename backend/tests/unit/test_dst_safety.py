"""Unit tests for DST transition safety check on time entries (#195).

Tests that when creating a time entry on a DST transition date, a warning
is logged. The creation itself is NOT blocked — only a warning is emitted.

Known DST transitions used:
- 2024-03-10: "spring forward" in America/New_York (clocks go 2:00 AM → 3:00 AM)
  The 2:00 AM hour does not exist (fold=False, but the hour is skipped).
- 2024-11-03: "fall back" in America/New_York (clocks go 2:00 AM → 1:00 AM)
  The 1:00-2:00 AM hour is repeated (fold ambiguity).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service_with_mocks(tenant_id: str = "tenant-001") -> tuple[object, MagicMock]:
    """Return (TimeEntriesService, mock_repo) pair with all FK checks pre-approved."""
    from app.services.time_entries_service import TimeEntriesService

    mock_db = MagicMock()
    svc = TimeEntriesService(mock_db, tenant_id)
    mock_repo = MagicMock()
    mock_repo.project_belongs_to_tenant = AsyncMock(return_value=True)
    mock_repo.employee_belongs_to_tenant = AsyncMock(return_value=True)
    svc._repo = mock_repo
    return svc, mock_repo


def _returned_row(tz: str = "America/New_York", entry_date: str = "2024-03-10") -> dict:
    return {
        "id": "te-001",
        "tenant_id": "tenant-001",
        "project_id": "proj-001",
        "employee_id": "emp-001",
        "date": entry_date,
        "hours": "8.00",
        "description": "",
        "billable": True,
        "billing_status": "unbilled",
        "status": "approved",
        "timezone": tz,
        "phase_id": None,
        "created_at": "2024-03-10T10:00:00+00:00",
        "updated_at": None,
    }


# ---------------------------------------------------------------------------
# Test 1: warning is logged when date is a spring-forward DST transition
# ---------------------------------------------------------------------------


def test_dst_spring_forward_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Creating a time entry on the spring-forward DST date logs a DST warning."""
    from app.models.time_entries import TimeEntryCreate
    from app.services.time_entries_service import TimeEntriesService

    svc, mock_repo = _make_service_with_mocks()
    mock_repo.create = AsyncMock(return_value=_returned_row("America/New_York", "2024-03-10"))

    data = TimeEntryCreate(
        project_id="proj-001",
        employee_id="emp-001",
        date=date(2024, 3, 10),  # spring-forward day in America/New_York
        hours=Decimal("8"),
        timezone="America/New_York",
    )

    async def _run() -> object:
        with patch(
            "app.services.time_entries_service.assert_period_open",
            new=AsyncMock(return_value=None),
        ):
            return await svc.create_entry(data, approved_by="user-001")

    with caplog.at_level(logging.WARNING, logger="app.services.time_entries_service"):
        asyncio.run(_run())

    dst_warnings = [r for r in caplog.records if "DST" in r.message or "dst" in r.message.lower()]
    assert dst_warnings, (
        "Expected a DST warning to be logged for 2024-03-10 in America/New_York"
    )


# ---------------------------------------------------------------------------
# Test 2: warning is logged when date is a fall-back DST transition (ambiguous)
# ---------------------------------------------------------------------------


def test_dst_fall_back_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Creating a time entry on the fall-back DST date logs a DST warning."""
    from app.models.time_entries import TimeEntryCreate

    svc, mock_repo = _make_service_with_mocks()
    mock_repo.create = AsyncMock(return_value=_returned_row("America/New_York", "2024-11-03"))

    data = TimeEntryCreate(
        project_id="proj-001",
        employee_id="emp-001",
        date=date(2024, 11, 3),  # fall-back day in America/New_York (fold)
        hours=Decimal("8"),
        timezone="America/New_York",
    )

    async def _run() -> object:
        with patch(
            "app.services.time_entries_service.assert_period_open",
            new=AsyncMock(return_value=None),
        ):
            return await svc.create_entry(data, approved_by="user-001")

    with caplog.at_level(logging.WARNING, logger="app.services.time_entries_service"):
        asyncio.run(_run())

    dst_warnings = [r for r in caplog.records if "DST" in r.message or "dst" in r.message.lower()]
    assert dst_warnings, (
        "Expected a DST warning to be logged for 2024-11-03 in America/New_York"
    )


# ---------------------------------------------------------------------------
# Test 3: no warning for a normal (non-DST-transition) day
# ---------------------------------------------------------------------------


def test_dst_normal_day_no_warning(caplog: pytest.LogCaptureFixture) -> None:
    """No DST warning is logged for a regular business day."""
    from app.models.time_entries import TimeEntryCreate

    svc, mock_repo = _make_service_with_mocks()
    mock_repo.create = AsyncMock(return_value=_returned_row("America/New_York", "2024-06-15"))

    data = TimeEntryCreate(
        project_id="proj-001",
        employee_id="emp-001",
        date=date(2024, 6, 15),  # midsummer, no DST transition
        hours=Decimal("8"),
        timezone="America/New_York",
    )

    async def _run() -> object:
        with patch(
            "app.services.time_entries_service.assert_period_open",
            new=AsyncMock(return_value=None),
        ):
            return await svc.create_entry(data, approved_by="user-001")

    with caplog.at_level(logging.WARNING, logger="app.services.time_entries_service"):
        asyncio.run(_run())

    dst_warnings = [r for r in caplog.records if "DST" in r.message or "dst" in r.message.lower()]
    assert not dst_warnings, (
        "No DST warning expected for 2024-06-15 in America/New_York"
    )


# ---------------------------------------------------------------------------
# Test 4: DST check does NOT block creation — entry is still returned
# ---------------------------------------------------------------------------


def test_dst_warning_does_not_block_creation() -> None:
    """A DST-transition date still results in a successfully created entry."""
    from app.models.time_entries import TimeEntryCreate, TimeEntryResponse

    svc, mock_repo = _make_service_with_mocks()
    mock_repo.create = AsyncMock(return_value=_returned_row("America/New_York", "2024-03-10"))

    data = TimeEntryCreate(
        project_id="proj-001",
        employee_id="emp-001",
        date=date(2024, 3, 10),
        hours=Decimal("8"),
        timezone="America/New_York",
    )

    async def _run() -> object:
        with patch(
            "app.services.time_entries_service.assert_period_open",
            new=AsyncMock(return_value=None),
        ):
            return await svc.create_entry(data, approved_by="user-001")

    result = asyncio.run(_run())
    assert isinstance(result, TimeEntryResponse)
    assert result.id == "te-001"


# ---------------------------------------------------------------------------
# Test 5: UTC timezone entries skip DST check (UTC has no DST)
# ---------------------------------------------------------------------------


def test_utc_entries_no_dst_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Time entries with timezone=UTC never trigger a DST warning."""
    from app.models.time_entries import TimeEntryCreate

    svc, mock_repo = _make_service_with_mocks()
    mock_repo.create = AsyncMock(return_value=_returned_row("UTC", "2024-03-10"))

    data = TimeEntryCreate(
        project_id="proj-001",
        employee_id="emp-001",
        date=date(2024, 3, 10),  # spring-forward in NY but irrelevant for UTC entries
        hours=Decimal("8"),
        timezone="UTC",
    )

    async def _run() -> object:
        with patch(
            "app.services.time_entries_service.assert_period_open",
            new=AsyncMock(return_value=None),
        ):
            return await svc.create_entry(data, approved_by="user-001")

    with caplog.at_level(logging.WARNING, logger="app.services.time_entries_service"):
        asyncio.run(_run())

    dst_warnings = [r for r in caplog.records if "DST" in r.message or "dst" in r.message.lower()]
    assert not dst_warnings, "No DST warning expected for UTC timezone"
