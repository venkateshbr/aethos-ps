"""Schema-drift fallbacks for bills repository writes."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from postgrest.exceptions import APIError

from app.repositories.bills_repo import BillsRepository

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-bills-fallback"


def test_create_retries_without_optional_po_match_columns_when_schema_lags() -> None:
    repo, first_insert, retry_insert = _make_repo_for_stale_bill_create()

    row = asyncio.run(
        repo.create(
            {
                "client_id": "vendor-1",
                "currency": "USD",
                "status": "draft",
                "po_match_status": "not_linked",
                "po_match_summary": {},
            }
        )
    )

    assert row["id"] == "bill-1"
    first_insert.insert.assert_called_once()
    retry_insert.insert.assert_called_once()
    retry_payload = retry_insert.insert.call_args.args[0]
    assert retry_payload["tenant_id"] == TENANT_ID
    assert retry_payload["client_id"] == "vendor-1"
    assert "po_match_status" not in retry_payload
    assert "po_match_summary" not in retry_payload


def test_create_line_retries_without_optional_prepaid_columns_when_schema_lags() -> None:
    repo, first_insert, retry_insert = _make_repo_for_stale_line_create()

    row = asyncio.run(
        repo.create_line(
            "bill-1",
            {
                "description": "Cloud hosting",
                "quantity": "1",
                "unit_price": "100.00",
                "amount": "100.00",
                "tax_amount": "0.00",
                "is_prepaid": False,
            },
        )
    )

    assert row["id"] == "line-1"
    first_insert.insert.assert_called_once()
    retry_insert.insert.assert_called_once()
    retry_payload = retry_insert.insert.call_args.args[0]
    assert retry_payload["tenant_id"] == TENANT_ID
    assert retry_payload["bill_id"] == "bill-1"
    assert "is_prepaid" not in retry_payload
    assert "service_start_date" not in retry_payload
    assert "service_end_date" not in retry_payload


def _make_repo_for_stale_bill_create() -> tuple[BillsRepository, MagicMock, MagicMock]:
    result = MagicMock()
    result.data = [
        {
            "id": "bill-1",
            "tenant_id": TENANT_ID,
            "client_id": "vendor-1",
            "currency": "USD",
            "status": "draft",
            "created_at": "2026-06-22T00:00:00",
        }
    ]
    first_insert = _chain(error=_missing_column_error("po_match_status"))
    retry_insert = _chain(result=result)
    mock_db = MagicMock()
    mock_db.table.side_effect = [first_insert, retry_insert]
    return BillsRepository(db=mock_db, tenant_id=TENANT_ID), first_insert, retry_insert


def _make_repo_for_stale_line_create() -> tuple[BillsRepository, MagicMock, MagicMock]:
    result = MagicMock()
    result.data = [
        {
            "id": "line-1",
            "tenant_id": TENANT_ID,
            "bill_id": "bill-1",
            "description": "Cloud hosting",
            "quantity": "1",
            "unit_price": "100.00",
            "amount": "100.00",
            "tax_amount": "0.00",
            "created_at": "2026-06-22T00:00:00",
        }
    ]
    first_insert = _chain(error=_missing_column_error("is_prepaid"))
    retry_insert = _chain(result=result)
    mock_db = MagicMock()
    mock_db.table.side_effect = [first_insert, retry_insert]
    return BillsRepository(db=mock_db, tenant_id=TENANT_ID), first_insert, retry_insert


def _missing_column_error(column_name: str) -> APIError:
    return APIError(
        {
            "code": "PGRST204",
            "message": f"Could not find the '{column_name}' column of 'bills' in the schema cache",
        }
    )


def _chain(result: object | None = None, error: Exception | None = None) -> MagicMock:
    chain = MagicMock()
    for method in ("select", "eq", "is_", "in_", "ilike", "insert", "update", "limit", "order"):
        getattr(chain, method).return_value = chain
    if error is not None:
        chain.execute.side_effect = error
    else:
        chain.execute.return_value = result
    return chain
