"""Unit tests for TimesheetService guard paths (issue #134, P4).

Uses MagicMock chains (no DB) to assert the self-only / status guards:
  - create on an unassigned project → 403
  - edit/delete a locked (submitted/approved) entry → 409
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.timesheet import TimesheetEntryCreate, TimesheetEntryUpdate
from app.services.timesheet_service import TimesheetService

pytestmark = pytest.mark.unit

TENANT = "t1"
EMP = "e1"


def _chain(data: list[dict]) -> MagicMock:
    result = MagicMock()
    result.data = data
    chain = MagicMock()
    for m in ("select", "eq", "in_", "is_", "gte", "lte", "limit", "order", "update", "insert", "delete"):
        getattr(chain, m).return_value = chain
    chain.execute.return_value = result
    return chain


def _svc(table_data: list[dict]) -> TimesheetService:
    db = MagicMock()
    db.table.return_value = _chain(table_data)
    return TimesheetService(db, TENANT, EMP)


@pytest.mark.asyncio
async def test_create_on_unassigned_project_is_forbidden() -> None:
    # _is_assigned query returns [] → not assigned.
    svc = _svc([])
    with pytest.raises(HTTPException) as exc:
        await svc.create_entry(
            TimesheetEntryCreate(project_id="p-unknown", date=date(2026, 5, 1), hours=Decimal("2"))
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_cannot_edit_submitted_entry() -> None:
    svc = _svc([{"id": "x", "status": "submitted", "tenant_id": TENANT, "employee_id": EMP,
                 "project_id": "p", "date": "2026-05-01", "hours": "2", "billable": True,
                 "billing_status": "unbilled", "created_at": "2026-05-01"}])
    with pytest.raises(HTTPException) as exc:
        await svc.update_entry("x", TimesheetEntryUpdate(hours=Decimal("3")))
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_cannot_delete_approved_entry() -> None:
    svc = _svc([{"id": "x", "status": "approved", "tenant_id": TENANT, "employee_id": EMP,
                 "project_id": "p", "date": "2026-05-01", "hours": "2", "billable": True,
                 "billing_status": "unbilled", "created_at": "2026-05-01"}])
    with pytest.raises(HTTPException) as exc:
        await svc.delete_entry("x")
    assert exc.value.status_code == 409
