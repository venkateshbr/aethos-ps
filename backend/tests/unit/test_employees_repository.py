"""Employees repository compatibility tests."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from postgrest.exceptions import APIError

from app.repositories.employees_repo import EmployeesRepository

pytestmark = pytest.mark.unit


def test_create_retries_without_optional_profile_columns_when_schema_lags() -> None:
    repo, first_insert, retry_insert = _make_repo_for_stale_profile_create()

    row = asyncio.run(
        repo.create(
            {
                "first_name": "Cara",
                "last_name": "Iyer",
                "email": "cara@example.com",
                "employment_type": "full_time",
                "target_billable_utilization_pct": "75",
                "practice_area": "accounting",
                "seniority": "associate",
            }
        )
    )

    assert row["id"] == "employee-created"
    first_insert.insert.assert_called_once()
    retry_insert.insert.assert_called_once()
    retry_payload = retry_insert.insert.call_args.args[0]
    assert retry_payload["tenant_id"] == "tenant-123"
    assert "target_billable_utilization_pct" not in retry_payload
    assert "practice_area" not in retry_payload
    assert "seniority" not in retry_payload


def test_update_retries_without_optional_profile_columns_when_schema_lags() -> None:
    repo, first_update, retry_update = _make_repo_for_stale_profile_update()

    row = asyncio.run(
        repo.update(
            "employee-1",
            {
                "title": "Senior Consultant",
                "target_billable_utilization_pct": "80",
            },
        )
    )

    assert row is not None
    assert row["title"] == "Senior Consultant"
    first_update.update.assert_called_once()
    retry_update.update.assert_called_once()
    retry_payload = retry_update.update.call_args.args[0]
    assert retry_payload["title"] == "Senior Consultant"
    assert "updated_at" in retry_payload
    assert "target_billable_utilization_pct" not in retry_payload


def _missing_profile_column_error() -> APIError:
    return APIError(
        {
            "code": "PGRST204",
            "message": "Could not find the 'target_billable_utilization_pct' "
            "column of 'employees' in the schema cache",
        }
    )


def _chain(result: object | None = None, error: Exception | None = None) -> MagicMock:
    chain = MagicMock()
    for method in ("select", "eq", "is_", "ilike", "neq", "or_", "order", "limit", "insert", "update"):
        getattr(chain, method).return_value = chain
    if error is not None:
        chain.execute.side_effect = error
    else:
        chain.execute.return_value = result
    return chain


def _make_repo_for_stale_profile_create() -> tuple[EmployeesRepository, MagicMock, MagicMock]:
    result = MagicMock()
    result.data = [
        {
            "id": "employee-created",
            "tenant_id": "tenant-123",
            "first_name": "Cara",
            "last_name": "Iyer",
            "email": "cara@example.com",
            "employment_type": "full_time",
            "status": "active",
            "created_at": "2026-01-01T00:00:00",
        }
    ]
    first_insert = _chain(error=_missing_profile_column_error())
    retry_insert = _chain(result=result)
    mock_db = MagicMock()
    mock_db.table.side_effect = [first_insert, retry_insert]
    return EmployeesRepository(db=mock_db, tenant_id="tenant-123"), first_insert, retry_insert


def _make_repo_for_stale_profile_update() -> tuple[EmployeesRepository, MagicMock, MagicMock]:
    updated = MagicMock()
    updated.data = [
        {
            "id": "employee-1",
            "tenant_id": "tenant-123",
            "first_name": "Cara",
            "last_name": "Iyer",
            "email": "cara@example.com",
            "employment_type": "full_time",
            "title": "Senior Consultant",
            "status": "active",
            "created_at": "2026-01-01T00:00:00",
        }
    ]
    first_update = _chain(error=_missing_profile_column_error())
    retry_update = _chain(result=updated)
    mock_db = MagicMock()
    mock_db.table.side_effect = [first_update, retry_update]
    return EmployeesRepository(db=mock_db, tenant_id="tenant-123"), first_update, retry_update
