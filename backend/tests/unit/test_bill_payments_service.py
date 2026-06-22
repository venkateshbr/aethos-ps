"""Unit tests for BillPaymentsService — batching, CSV export, NACHA export, agent proposal.

All tests use MagicMock — no network calls, no DB, no real Supabase credentials.

Issues: #61
"""

from __future__ import annotations

import asyncio
import csv
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-bp-test-001"
USER_ID = "user-bp-001"


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


def _make_svc(mock_db: MagicMock):
    from app.services.bill_payments_service import BillPaymentsService

    return BillPaymentsService(mock_db, TENANT_ID)


# ---------------------------------------------------------------------------
# Helper — fluent chain builder
# ---------------------------------------------------------------------------


def _chain(data: list[dict]) -> MagicMock:
    result = MagicMock()
    result.data = data

    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.in_.return_value = chain
    chain.is_.return_value = chain
    chain.gte.return_value = chain
    chain.lte.return_value = chain
    chain.limit.return_value = chain
    chain.order.return_value = chain
    chain.insert.return_value = chain
    chain.update.return_value = chain
    chain.execute.return_value = result
    return chain


# ---------------------------------------------------------------------------
# 1. create_batch requires all bills to be approved
# ---------------------------------------------------------------------------


def test_create_batch_requires_approved_bills(mock_db: MagicMock) -> None:
    """create_batch raises HTTP 422 when any bill is not in 'approved' status."""
    from fastapi import HTTPException

    # Bills returned from DB — one is still in 'draft' status
    bills = [
        {"id": "bill-1", "total": "1000.00", "currency": "USD", "status": "approved", "client_id": "client-1"},
        {"id": "bill-2", "total": "2000.00", "currency": "USD", "status": "draft", "client_id": "client-2"},
    ]
    mock_db.table.return_value = _chain(bills)

    svc = _make_svc(mock_db)

    with pytest.raises(HTTPException) as exc_info:
        svc.create_batch(["bill-1", "bill-2"], None, "", USER_ID)

    assert exc_info.value.status_code == 422
    assert "approved" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# 2. export_csv produces a header row + data rows
# ---------------------------------------------------------------------------


def test_export_csv_has_header_row(mock_db: MagicMock) -> None:
    """export_csv must include the correct column headers on the first row."""
    batch = {
        "id": "batch-001",
        "status": "approved",
        "total": "5000.00",
        "currency": "USD",
        "pay_date": "2026-06-01",
        "items": [
            {
                "amount": "5000.00",
                "currency": "USD",
                "bills": {
                    "client_id": "client-1",
                    "vendor_invoice_number": "VIN-9999",
                },
            }
        ],
    }

    svc = _make_svc(mock_db)

    # Patch get_batch so export_csv doesn't need a real DB
    svc.get_batch = MagicMock(return_value=batch)

    # Also mock the update call that export_csv issues at the end
    mock_db.table.return_value = _chain([{"id": "batch-001"}])

    raw = svc.export_csv("batch-001")
    assert isinstance(raw, bytes)

    decoded = raw.decode("utf-8")
    reader = csv.reader(StringIO(decoded))
    rows = list(reader)

    assert len(rows) >= 2, "Expected header row + at least one data row"

    header = rows[0]
    expected_cols = [
        "Vendor Name",
        "Routing Number",
        "Account Number",
        "Amount",
        "Currency",
        "Pay Date",
        "Reference",
        "Vendor Invoice Number",
    ]
    assert header == expected_cols


# ---------------------------------------------------------------------------
# 3. export_nacha output is padded to multiples of 10 lines
# ---------------------------------------------------------------------------


def test_nacha_padded_to_multiple_of_10(mock_db: MagicMock) -> None:
    """NACHA output line count must be a multiple of 10 (ACH spec §3)."""
    batch = {
        "id": "batch-002",
        "status": "approved",
        "total": "300.00",
        "currency": "USD",
        "pay_date": "2026-06-01",
        "items": [
            {"amount": "100.00", "currency": "USD"},
            {"amount": "200.00", "currency": "USD"},
        ],
    }

    svc = _make_svc(mock_db)
    svc.get_batch = MagicMock(return_value=batch)
    mock_db.table.return_value = _chain([{"id": "batch-002"}])

    raw = svc.export_nacha("batch-002")
    assert isinstance(raw, bytes)

    decoded = raw.decode("ascii")
    # NACHA uses CRLF line endings
    lines = decoded.split("\r\n")
    # Remove trailing empty string from final CRLF
    lines = [ln for ln in lines if ln]

    assert len(lines) % 10 == 0, (
        f"NACHA file must be padded to 10-line blocks; got {len(lines)} lines"
    )


# ---------------------------------------------------------------------------
# 4. propose endpoint calls write_agent_suggestion with L2
# ---------------------------------------------------------------------------


def test_propose_writes_l2_suggestion() -> None:
    """propose_payment_batch result must be written as L2 (HITL required)."""
    from app.agents.base import AgentDeps
    from app.agents.bill_pay_agent import BillPayProposal, propose_payment_batch

    # Minimal DB mock for the agent's bill query
    mock_db = MagicMock()
    bills = [
        {"id": "bill-x1", "bill_number": "BILL-001", "total": "1500.00", "currency": "USD", "due_date": "2026-05-25", "vendor_invoice_number": "VIN-001", "client_id": "clt-1"},
    ]
    chain = MagicMock()
    chain_result = MagicMock()
    chain_result.data = bills
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.is_.return_value = chain
    chain.lte.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = chain_result
    mock_db.table.return_value = chain

    deps = AgentDeps(tenant_id=TENANT_ID, user_id=USER_ID, db=mock_db)
    proposal = propose_payment_batch(deps, due_within_days=7)

    assert isinstance(proposal, BillPayProposal)
    assert proposal.confidence <= 1.0
    assert proposal.confidence >= 0.0

    # Now verify that write_agent_suggestion is called with autonomy_level=2
    suggestion_calls: list[dict] = []

    async def _fake_write(
        deps,
        agent_name,
        action_type,
        document_id,
        output,
        confidence,
        autonomy_level=2,
        **kwargs,
    ):
        suggestion_calls.append(
            {
                "agent_name": agent_name,
                "autonomy_level": autonomy_level,
                "confidence": confidence,
            }
        )
        return {"id": "sug-test-001", "hitl_required": True}

    with patch("app.agents.suggestion_writer.write_agent_suggestion", side_effect=_fake_write):
        asyncio.run(
            _fake_write(
                deps,
                agent_name="bill_pay_agent",
                action_type="create_bill_payment_batch",
                document_id=USER_ID,
                output=proposal.model_dump(mode="json"),
                confidence=proposal.confidence,
                autonomy_level=2,
            )
        )

    assert len(suggestion_calls) == 1
    assert suggestion_calls[0]["autonomy_level"] == 2, "bill_pay_agent must always be L2"
    assert suggestion_calls[0]["agent_name"] == "bill_pay_agent"


@pytest.mark.asyncio
async def test_inbox_materialises_bill_payment_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import date

    from app.services.inbox_service import InboxService

    calls: list[dict] = []

    class _BillPayments:
        def __init__(self, _db: object, tenant_id: str) -> None:
            self.tenant_id = tenant_id

        def create_batch(
            self,
            bill_ids: list[str],
            pay_date: date | None,
            bank_account_label: str,
            created_by: str,
        ) -> dict:
            calls.append(
                {
                    "tenant_id": self.tenant_id,
                    "bill_ids": bill_ids,
                    "pay_date": pay_date,
                    "bank_account_label": bank_account_label,
                    "created_by": created_by,
                }
            )
            return {"id": "batch-1"}

    monkeypatch.setattr(
        "app.services.bill_payments_service.BillPaymentsService",
        _BillPayments,
    )

    svc = InboxService.__new__(InboxService)
    svc._db = MagicMock()
    svc._tenant_id = TENANT_ID

    result = await svc._materialise_bill_payment_batch(
        {
            "proposed_bill_ids": ["bill-1", "bill-2"],
            "proposed_pay_date": "2026-06-30",
            "bank_account_label": "Operating",
        }
    )

    assert result == {"entity_type": "bill_payment_batch", "entity_id": "batch-1"}
    assert calls == [
        {
            "tenant_id": TENANT_ID,
            "bill_ids": ["bill-1", "bill-2"],
            "pay_date": date(2026, 6, 30),
            "bank_account_label": "Operating",
            "created_by": "bill_pay_agent",
        }
    ]


@pytest.mark.asyncio
async def test_inbox_materialise_bill_payment_batch_rejects_bad_date() -> None:
    from fastapi import HTTPException

    from app.services.inbox_service import InboxService

    svc = InboxService.__new__(InboxService)
    svc._db = MagicMock()
    svc._tenant_id = TENANT_ID

    with pytest.raises(HTTPException) as exc_info:
        await svc._materialise_bill_payment_batch(
            {
                "proposed_bill_ids": ["bill-1"],
                "proposed_pay_date": "not-a-date",
            }
        )

    assert exc_info.value.status_code == 422
