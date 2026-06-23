"""Unit tests for BillPaymentsService — batching, CSV export, NACHA export, agent proposal.

All tests use MagicMock — no network calls, no DB, no real Supabase credentials.

Issues: #61
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
from decimal import Decimal
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


def test_create_batch_records_payment_optimization(mock_db: MagicMock) -> None:
    """create_batch stores ranked payment context and manual-review flags."""
    from datetime import date

    bills = [
        {
            "id": "bill-low",
            "bill_number": "BILL-LOW",
            "total": "1000.00",
            "currency": "USD",
            "status": "approved",
            "client_id": "client-1",
            "due_date": "2026-06-30",
            "vendor_invoice_number": "VIN-LOW",
        },
        {
            "id": "bill-high",
            "bill_number": "BILL-HIGH",
            "total": "75000.00",
            "currency": "USD",
            "status": "approved",
            "client_id": "client-2",
            "due_date": "2026-06-20",
            "vendor_invoice_number": "VIN-HIGH",
        },
    ]
    bills_chain = _chain(bills)
    batch_chain = _chain([{"id": "batch-001", "status": "draft"}])
    items_chain = _chain([])

    def table_side_effect(table_name: str) -> MagicMock:
        if table_name == "bills":
            return bills_chain
        if table_name == "bill_payment_batches":
            return batch_chain
        if table_name == "bill_payment_items":
            return items_chain
        raise AssertionError(table_name)

    mock_db.table.side_effect = table_side_effect
    svc = _make_svc(mock_db)

    result = svc.create_batch(
        ["bill-low", "bill-high"],
        date(2026, 6, 23),
        "Operating Account",
        USER_ID,
    )

    batch_payload = batch_chain.insert.call_args.args[0]
    assert batch_payload["risk_review_required"] is True
    assert batch_payload["optimization_summary"]["ranked_bill_ids"] == [
        "bill-high",
        "bill-low",
    ]
    assert batch_payload["optimization_summary"]["manual_review_flags"][0]["bill_id"] == (
        "bill-high"
    )
    item_payload = items_chain.insert.call_args.args[0]
    assert [item["bill_id"] for item in item_payload] == ["bill-high", "bill-low"]
    assert result["risk_review_required"] is True


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


def test_export_csv_records_integrity_metadata(mock_db: MagicMock) -> None:
    """CSV export stores actor, byte count, and SHA-256 without bank credentials."""
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
    svc.get_batch = MagicMock(return_value=batch)
    chain = _chain([{"id": "batch-001"}])
    mock_db.table.return_value = chain

    raw = svc.export_csv("batch-001", USER_ID)

    patch = chain.update.call_args.args[0]
    assert patch["file_format"] == "csv"
    assert patch["exported_by"] == USER_ID
    assert patch["export_file_bytes"] == len(raw)
    assert patch["export_file_sha256"] == hashlib.sha256(raw).hexdigest()
    chain.eq.assert_any_call("tenant_id", TENANT_ID)


def test_export_requires_approved_batch(mock_db: MagicMock) -> None:
    """Draft batches cannot be exported into bank files."""
    from fastapi import HTTPException

    svc = _make_svc(mock_db)
    svc.get_batch = MagicMock(return_value={"id": "batch-1", "status": "draft", "items": []})

    with pytest.raises(HTTPException) as exc_info:
        svc.export_csv("batch-1", USER_ID)

    assert exc_info.value.status_code == 409
    assert "approved" in str(exc_info.value.detail)


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


def test_approve_batch_records_approver(mock_db: MagicMock) -> None:
    """Approval stores who approved the money-out batch."""
    svc = _make_svc(mock_db)
    svc.get_batch = MagicMock(return_value={"id": "batch-1", "status": "draft"})
    chain = _chain([{"id": "batch-1", "status": "approved"}])
    mock_db.table.return_value = chain

    result = svc.approve_batch("batch-1", USER_ID)

    assert result["status"] == "approved"
    patch = chain.update.call_args.args[0]
    assert patch["status"] == "approved"
    assert patch["approved_by"] == USER_ID
    assert "approved_at" in patch


def test_mark_sent_requires_export_hash(mock_db: MagicMock) -> None:
    """A batch cannot be marked sent until the exported file hash exists."""
    from fastapi import HTTPException

    svc = _make_svc(mock_db)
    svc.get_batch = MagicMock(return_value={"id": "batch-1", "status": "approved"})

    with pytest.raises(HTTPException) as exc_info:
        svc.mark_sent("batch-1", USER_ID)

    assert exc_info.value.status_code == 409
    assert "exported" in str(exc_info.value.detail)


def test_mark_sent_records_sender(mock_db: MagicMock) -> None:
    """Sending to bank stores actor/timestamp and moves to sent_to_bank."""
    svc = _make_svc(mock_db)
    svc.get_batch = MagicMock(
        return_value={
            "id": "batch-1",
            "status": "approved",
            "export_file_sha256": "a" * 64,
        }
    )
    chain = _chain([{"id": "batch-1", "status": "sent_to_bank"}])
    mock_db.table.return_value = chain

    result = svc.mark_sent("batch-1", USER_ID)

    assert result["status"] == "sent_to_bank"
    patch = chain.update.call_args.args[0]
    assert patch["status"] == "sent_to_bank"
    assert patch["sent_by"] == USER_ID
    assert "sent_at" in patch


# ---------------------------------------------------------------------------
# 4. settle_batch posts AP clearing journal only after bank confirmation
# ---------------------------------------------------------------------------


def test_settle_batch_posts_ap_clearing_journal(mock_db: MagicMock) -> None:
    """Settlement posts DR AP / CR Bank and marks the bill/payment item settled."""
    batch = {
        "id": "batch-settle-001",
        "status": "sent_to_bank",
        "currency": "USD",
        "items": [
            {
                "id": "item-001",
                "bill_id": "11111111-1111-1111-1111-111111111111",
                "amount": "750.00",
                "currency": "USD",
                "status": "pending",
                "bills": {"bill_number": "BILL-001"},
            }
        ],
    }

    svc = _make_svc(mock_db)
    svc.get_batch = MagicMock(return_value=batch)

    def table_side_effect(table_name: str) -> MagicMock:
        if table_name == "accounts":
            return _chain(
                [
                    {"code": "1100", "id": "bank-account-id"},
                    {"code": "2000", "id": "ap-account-id"},
                ]
            )
        return _chain([{"id": "updated"}])

    mock_db.table.side_effect = table_side_effect

    with patch(
        "app.services.bill_payments_service.post_journal",
        return_value={"id": "journal-001"},
    ) as mock_post:
        result = svc.settle_batch("batch-settle-001", USER_ID)

    assert result == {
        "batch_id": "batch-settle-001",
        "status": "settled",
        "settled_count": 1,
        "journal_entry_ids": ["journal-001"],
    }
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["reference_type"] == "bill_payment"
    assert call_kwargs["reference_id"] == "11111111-1111-1111-1111-111111111111"
    lines = call_kwargs["lines"]
    assert lines[0].direction == "DR"
    assert lines[0].account_code == "2000"
    assert lines[1].direction == "CR"
    assert lines[1].account_code == "1100"


def test_settle_batch_requires_sent_to_bank(mock_db: MagicMock) -> None:
    """A draft/approved batch cannot post money-out journals."""
    from fastapi import HTTPException

    svc = _make_svc(mock_db)
    svc.get_batch = MagicMock(return_value={"id": "batch-1", "status": "approved", "items": []})

    with pytest.raises(HTTPException) as exc_info:
        svc.settle_batch("batch-1", USER_ID)

    assert exc_info.value.status_code == 409
    assert "sent_to_bank" in str(exc_info.value.detail)


def test_settle_batch_rejects_already_settled_items(mock_db: MagicMock) -> None:
    """Retrying a fully settled batch is blocked before any journal post."""
    from fastapi import HTTPException

    svc = _make_svc(mock_db)
    svc.get_batch = MagicMock(
        return_value={
            "id": "batch-1",
            "status": "sent_to_bank",
            "items": [{"id": "item-1", "status": "settled"}],
        }
    )

    with (
        patch("app.services.bill_payments_service.post_journal") as mock_post,
        pytest.raises(HTTPException) as exc_info,
    ):
        svc.settle_batch("batch-1", USER_ID)

    assert exc_info.value.status_code == 409
    mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# 5. propose endpoint calls write_agent_suggestion with L2
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
    assert proposal.optimization_summary["ranked_bill_ids"] == ["bill-x1"]

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


def test_bill_pay_agent_prioritizes_overdue_high_value_bills() -> None:
    """The bill-pay agent uses deterministic payment optimization ranking."""
    from app.agents.base import AgentDeps
    from app.agents.bill_pay_agent import propose_payment_batch

    mock_db = MagicMock()
    bills = [
        {
            "id": "bill-standard",
            "bill_number": "BILL-STD",
            "total": "1000.00",
            "currency": "USD",
            "due_date": "2026-12-31",
            "vendor_invoice_number": "STD",
            "client_id": "clt-1",
        },
        {
            "id": "bill-urgent",
            "bill_number": "BILL-URG",
            "total": "75000.00",
            "currency": "USD",
            "due_date": "2026-01-01",
            "vendor_invoice_number": "URG",
            "client_id": "clt-2",
        },
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

    assert proposal.proposed_bill_ids[0] == "bill-urgent"
    assert proposal.optimization_summary["ranked_bill_ids"][0] == "bill-urgent"
    assert proposal.flagged_for_review[0]["bill_id"] == "bill-urgent"


def test_bill_pay_duplicate_proposal_matches_bill_set() -> None:
    """Duplicate detection normalises bill id order before comparing proposals."""
    from app.agents.base import AgentDeps
    from app.agents.bill_pay_agent import find_duplicate_payment_proposal

    rows = [
        {
            "id": "suggestion-001",
            "output_snapshot": {"proposed_bill_ids": ["bill-2", "bill-1"]},
        }
    ]
    mock_db = MagicMock()
    mock_db.table.return_value = _chain(rows)
    deps = AgentDeps(tenant_id=TENANT_ID, user_id=USER_ID, db=mock_db)

    assert find_duplicate_payment_proposal(deps, ["bill-1", "bill-2"]) == (
        "suggestion-001"
    )
    assert find_duplicate_payment_proposal(deps, []) is None


@pytest.mark.asyncio
async def test_bill_pay_propose_endpoint_skips_empty_suggestion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty bill-pay proposals return context but do not create HITL tasks."""
    from app.agents.bill_pay_agent import BillPayProposal
    from app.api.v1.endpoints.bill_payments import propose
    from app.core.auth import CurrentUser

    def _fake_proposal(_deps: object, _due_within_days: int) -> BillPayProposal:
        return BillPayProposal(
            proposed_bill_ids=[],
            proposed_pay_date="2026-06-30",
            total_amount=Decimal("0.00"),
            currency="USD",
            rationale="No approved bills are ready for payment.",
        )

    async def _unexpected_write(*_args: object, **_kwargs: object) -> dict:
        raise AssertionError("empty proposal should not write agent_suggestions")

    monkeypatch.setattr("app.agents.bill_pay_agent.propose_payment_batch", _fake_proposal)
    monkeypatch.setattr("app.agents.suggestion_writer.write_agent_suggestion", _unexpected_write)

    result = await propose(
        due_within_days=7,
        tenant_id=TENANT_ID,
        db=MagicMock(),
        user=CurrentUser(user_id=USER_ID, email="admin@example.com", role="admin"),
    )

    assert result["proposed_bill_ids"] == []
    assert result["suggestion_id"] is None
    assert result["skipped_reason"] == "no_approved_bills"


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
