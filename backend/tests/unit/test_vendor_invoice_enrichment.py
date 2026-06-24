"""Unit tests for vendor identity resolution and GL suggestion in vendor_invoice_agent.

These tests cover:
- Exact registration-number match shortcut (pre-LLM, high confidence)
- Exact-name fallback when LLM is unavailable
- _exact_name_match edge cases
- mask_registration_number / mask_address PII helpers
- VendorMatchResult / GLSuggestion schema validation
- Tax ID warnings surfaced through BillDraft.tax_id_warnings

All tests are pure-Python unit tests; no I/O, no LLM calls, no Supabase.
"""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# PII masking helpers
# ---------------------------------------------------------------------------


def test_mask_registration_number_short_input() -> None:
    from app.agents.base import mask_registration_number

    result = mask_registration_number("GB12")  # too short — <= 6 chars
    assert result == "[REDACTED-REGNUM]"


def test_mask_registration_number_normal() -> None:
    from app.agents.base import mask_registration_number

    result = mask_registration_number("GB123456789")
    assert result.startswith("GB12")
    assert result.endswith("89")
    assert "****" in result
    # Original digits not present verbatim in middle
    assert "34567" not in result


def test_mask_registration_number_ein() -> None:
    from app.agents.base import mask_registration_number

    result = mask_registration_number("12-3456789")
    assert result.startswith("12-3")
    assert result.endswith("89")
    assert "****" in result


def test_mask_address_single_segment() -> None:
    from app.agents.base import mask_address

    result = mask_address("United Kingdom")
    assert result == "[REDACTED-ADDR]"


def test_mask_address_multi_segment_keeps_last() -> None:
    from app.agents.base import mask_address

    result = mask_address("100 Main St, London, United Kingdom")
    assert "United Kingdom" in result
    assert "[REDACTED]" in result
    assert "Main St" not in result


def test_mask_address_empty() -> None:
    from app.agents.base import mask_address

    result = mask_address("")
    assert result == "[REDACTED-ADDR]"


def test_mask_address_none() -> None:
    from app.agents.base import mask_address

    result = mask_address(None)  # type: ignore[arg-type]
    assert result == "[REDACTED-ADDR]"


# ---------------------------------------------------------------------------
# VendorMatchResult schema
# ---------------------------------------------------------------------------


def test_vendor_match_result_no_match() -> None:
    from app.agents.schemas import VendorMatchResult

    r = VendorMatchResult(
        matched_client_id=None,
        confidence=0.0,
        match_reason="No match found",
    )
    assert r.matched_client_id is None
    assert r.confidence == 0.0


def test_vendor_match_result_with_uuid() -> None:
    from app.agents.schemas import VendorMatchResult

    r = VendorMatchResult(
        matched_client_id="00000000-0000-0000-0000-000000000001",  # type: ignore[arg-type]
        confidence=0.97,
        match_reason="Exact reg number match",
    )
    assert str(r.matched_client_id) == "00000000-0000-0000-0000-000000000001"
    assert r.confidence == 0.97


def test_vendor_match_result_confidence_clamped() -> None:
    from pydantic import ValidationError

    from app.agents.schemas import VendorMatchResult

    with pytest.raises(ValidationError):
        VendorMatchResult(matched_client_id=None, confidence=1.5, match_reason="x")


# ---------------------------------------------------------------------------
# GLSuggestion schema
# ---------------------------------------------------------------------------


def test_gl_suggestion_fields() -> None:
    from app.agents.schemas import GLSuggestion

    s = GLSuggestion(
        account_id="00000000-0000-0000-0000-000000000010",  # type: ignore[arg-type]
        account_code="5100",
        account_name="Software & SaaS",
        confidence=0.92,
    )
    assert s.account_code == "5100"
    assert s.confidence == 0.92


def test_gl_suggestion_low_confidence_allowed() -> None:
    from app.agents.schemas import GLSuggestion

    s = GLSuggestion(
        account_id="00000000-0000-0000-0000-000000000010",  # type: ignore[arg-type]
        account_code="5000",
        account_name="General Expenses",
        confidence=0.50,
    )
    assert s.confidence == 0.50


def test_vendor_invoice_output_includes_match_coding_and_exceptions() -> None:
    from app.agents.schemas import BillDraft, GLSuggestion, VendorMatchResult
    from app.workers.document_extraction import _normalise_vendor_invoice_output

    draft = BillDraft(
        vendor_name="AWS",
        vendor_invoice_number="AWS-100",
        currency="USD",
        subtotal=Decimal("100.00"),
        tax_total=Decimal("10.00"),
        total=Decimal("110.00"),
        lines=[{"description": "Cloud hosting", "amount": "100.00"}],
        confidence=0.88,
        possible_duplicate=True,
    )
    object.__setattr__(
        draft,
        "_vendor_match",
        VendorMatchResult(
            matched_client_id="00000000-0000-0000-0000-000000000001",  # type: ignore[arg-type]
            confidence=0.97,
            match_reason="Exact tax-id match",
        ),
    )
    object.__setattr__(
        draft,
        "_gl_suggestions",
        [
            GLSuggestion(
                account_id="00000000-0000-0000-0000-000000000010",  # type: ignore[arg-type]
                account_code="5100",
                account_name="Software",
                confidence=0.91,
            )
        ],
    )

    output = _normalise_vendor_invoice_output(draft.model_dump(mode="json"), draft)

    assert output["client_id"] == "00000000-0000-0000-0000-000000000001"
    assert output["vendor_match"]["match_reason"] == "Exact tax-id match"
    assert output["gl_suggestions"][0]["account_code"] == "5100"
    assert output["lines"][0]["account_id"] == "00000000-0000-0000-0000-000000000010"
    assert output["coding_status"] == "coded"
    assert output["match_status"] == "duplicate_review_required"
    assert output["review_exceptions"][0]["code"] == "possible_duplicate"


# ---------------------------------------------------------------------------
# _exact_name_match fallback
# ---------------------------------------------------------------------------


_VENDOR_UUID_1 = "00000000-0000-0000-0000-000000000001"
_VENDOR_UUID_2 = "00000000-0000-0000-0000-000000000002"
_VENDOR_UUID_3 = "00000000-0000-0000-0000-000000000003"


def test_exact_name_match_hit() -> None:
    from app.agents.vendor_invoice_agent import _exact_name_match

    vendors = [
        {"id": _VENDOR_UUID_1, "name": "AWS Inc.", "tax_id": None},
        {"id": _VENDOR_UUID_2, "name": "CloudPeak Systems", "tax_id": None},
    ]
    result = _exact_name_match("aws inc.", vendors)
    assert str(result.matched_client_id) == _VENDOR_UUID_1
    assert result.confidence == 0.80


def test_exact_name_match_miss() -> None:
    from app.agents.vendor_invoice_agent import _exact_name_match

    vendors = [{"id": _VENDOR_UUID_1, "name": "AWS Inc.", "tax_id": None}]
    result = _exact_name_match("Amazon Web Services", vendors)
    assert result.matched_client_id is None
    assert result.confidence == 0.0


def test_exact_name_match_empty_vendors() -> None:
    from app.agents.vendor_invoice_agent import _exact_name_match

    result = _exact_name_match("Acme Corp", [])
    assert result.matched_client_id is None
    assert result.confidence == 0.0


def test_exact_name_match_case_insensitive() -> None:
    from app.agents.vendor_invoice_agent import _exact_name_match

    vendors = [{"id": _VENDOR_UUID_3, "name": "CloudPeak Systems Pte Ltd", "tax_id": None}]
    result = _exact_name_match("cloudpeak systems pte ltd", vendors)
    assert str(result.matched_client_id) == _VENDOR_UUID_3


# ---------------------------------------------------------------------------
# BillDraft new fields
# ---------------------------------------------------------------------------


def test_bill_draft_new_vendor_fields_default_none() -> None:
    from app.agents.schemas import BillDraft

    d = BillDraft(
        vendor_name="Acme",
        subtotal=Decimal("100"),
        total=Decimal("100"),
        confidence=0.9,
    )
    assert d.vendor_registration_number is None
    assert d.vendor_address is None
    assert d.vendor_payment_terms_days is None
    assert d.tax_id_warnings == []


def test_bill_draft_tax_id_warnings_field() -> None:
    from app.agents.schemas import BillDraft

    d = BillDraft(
        vendor_name="Acme",
        subtotal=Decimal("100"),
        total=Decimal("100"),
        confidence=0.9,
        tax_id_warnings=["Mismatch: vendor address suggests UK but tax ID is US EIN."],
    )
    assert len(d.tax_id_warnings) == 1
    assert "Mismatch" in d.tax_id_warnings[0]


def test_bill_draft_vendor_registration_number_stored() -> None:
    from app.agents.schemas import BillDraft

    d = BillDraft(
        vendor_name="Acme UK",
        subtotal=Decimal("500"),
        total=Decimal("500"),
        confidence=0.88,
        vendor_registration_number="GB123456789",
        vendor_address="10 Downing St, London, United Kingdom",
    )
    assert d.vendor_registration_number == "GB123456789"
    assert d.vendor_address is not None


# ---------------------------------------------------------------------------
# resolve_vendor_identity — pre-LLM exact reg number match
# ---------------------------------------------------------------------------


_VENDOR_DB_UUID = "10000000-0000-0000-0000-000000000001"


def _make_vendor_db_mock(rows: list[dict]) -> MagicMock:
    """Build a Supabase-style mock that returns ``rows`` for _fetch_vendors_sync.

    _fetch_vendors_sync calls:
        db.table("clients").select(...).eq("tenant_id",...).in_("kind",...).is_(...).limit(...).execute()
    MagicMock auto-creates chained attribute access — every return_value is also
    a MagicMock, so we only need to pin the terminal .execute().data value.
    The trick: use a single MagicMock for all intermediate steps so that ANY
    chain of method calls eventually reaches the same execute().data.
    """
    mock_db = MagicMock()
    execute_result = MagicMock()
    execute_result.data = rows

    # Build a single "chain" mock that always returns itself from any call,
    # except .execute() which returns execute_result.
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.in_.return_value = chain
    chain.is_.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = execute_result

    mock_db.table.return_value = chain
    return mock_db


def test_resolve_vendor_exact_reg_number_match() -> None:
    """Pre-LLM path: exact registration number match returns confidence ≥ 0.95."""
    from app.agents.base import AgentDeps
    from app.agents.vendor_invoice_agent import resolve_vendor_identity

    mock_db = _make_vendor_db_mock([
        {"id": _VENDOR_DB_UUID, "name": "AWS Inc.", "tax_id": "12-3456789", "kind": "vendor"},
    ])
    deps = AgentDeps(tenant_id="tenant-1", user_id=None, db=mock_db)

    result = asyncio.run(
        resolve_vendor_identity("Amazon Web Services", "12-3456789", deps)
    )
    assert result.matched_client_id is not None
    assert str(result.matched_client_id) == _VENDOR_DB_UUID
    assert result.confidence >= 0.95
    assert "registration number" in result.match_reason.lower()


def test_resolve_vendor_no_existing_vendors() -> None:
    """No existing vendors → suggest creating new."""
    from app.agents.base import AgentDeps
    from app.agents.vendor_invoice_agent import resolve_vendor_identity

    mock_db = _make_vendor_db_mock([])
    deps = AgentDeps(tenant_id="tenant-1", user_id=None, db=mock_db)

    result = asyncio.run(
        resolve_vendor_identity("New Vendor Co", None, deps)
    )
    assert result.matched_client_id is None
    assert result.confidence == 0.0


def test_resolve_vendor_db_failure_returns_no_match() -> None:
    """DB failure on vendor fetch → returns no-match result (graceful degradation)."""
    from app.agents.base import AgentDeps
    from app.agents.vendor_invoice_agent import resolve_vendor_identity

    mock_db = MagicMock()
    mock_db.table.side_effect = Exception("DB unavailable")

    deps = AgentDeps(tenant_id="tenant-1", user_id=None, db=mock_db)

    result = asyncio.run(
        resolve_vendor_identity("Some Vendor", None, deps)
    )
    # Graceful degradation — no exception raised
    assert result.matched_client_id is None


# ---------------------------------------------------------------------------
# suggest_gl_account — no accounts → returns None
# ---------------------------------------------------------------------------


def test_suggest_gl_account_no_accounts_returns_none() -> None:
    from app.agents.base import AgentDeps
    from app.agents.vendor_invoice_agent import suggest_gl_account

    mock_db = MagicMock()
    deps = AgentDeps(tenant_id="tenant-1", user_id=None, db=mock_db)

    result = asyncio.run(
        suggest_gl_account("Cloud compute costs", [], deps)
    )
    assert result is None


def test_fetch_coa_accounts_uses_account_type_column() -> None:
    from app.agents.base import AgentDeps
    from app.agents.vendor_invoice_agent import _fetch_coa_accounts_sync

    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.is_.return_value = chain
    chain.order.return_value = chain
    chain.execute.return_value.data = [
        {
            "id": "00000000-0000-0000-0000-000000000010",
            "code": "5000",
            "name": "General Expenses",
            "account_type": "expense",
        }
    ]
    mock_db = MagicMock()
    mock_db.table.return_value = chain
    deps = AgentDeps(tenant_id="tenant-1", user_id=None, db=mock_db)

    result = _fetch_coa_accounts_sync(deps)

    chain.select.assert_called_once_with("id, code, name, account_type")
    assert result[0]["account_type"] == "expense"


def test_suggest_gl_account_filters_by_account_type() -> None:
    from app.agents.base import AgentDeps
    from app.agents.vendor_invoice_agent import suggest_gl_account

    expense_id = "00000000-0000-0000-0000-000000000010"
    revenue_id = "00000000-0000-0000-0000-000000000020"
    accounts = [
        {
            "id": expense_id,
            "code": "5000",
            "name": "General Expenses",
            "account_type": "expense",
        },
        {
            "id": revenue_id,
            "code": "4000",
            "name": "Revenue",
            "account_type": "revenue",
        },
    ]
    mock_db = MagicMock()
    deps = AgentDeps(tenant_id="tenant-1", user_id=None, db=mock_db)

    async def _fake_create(**kwargs):
        prompt = kwargs["messages"][0]["content"]
        assert "5000" in prompt
        assert "4000" not in prompt
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            {
                                "account_id": expense_id,
                                "account_code": "5000",
                                "account_name": "General Expenses",
                                "confidence": 0.91,
                            }
                        )
                    )
                )
            ]
        )

    with patch("app.agents.vendor_invoice_agent.make_async_llm_client") as mock_client:
        mock_client.return_value.chat.completions.create = AsyncMock(
            side_effect=_fake_create
        )

        result = asyncio.run(suggest_gl_account("Software license", accounts, deps))

    assert result is not None
    assert str(result.account_id) == expense_id
    assert result.account_code == "5000"


def test_suggest_gl_account_llm_failure_returns_none() -> None:
    """LLM call failure → graceful degradation returns None."""
    from app.agents.base import AgentDeps
    from app.agents.vendor_invoice_agent import suggest_gl_account

    accounts = [
        {"id": "acct-1", "code": "5000", "name": "General Expenses", "type": "expense"},
    ]
    mock_db = MagicMock()
    deps = AgentDeps(tenant_id="tenant-1", user_id=None, db=mock_db)

    with patch("app.agents.vendor_invoice_agent.make_async_llm_client") as mock_client:
        mock_client.return_value.chat.completions.create = AsyncMock(
            side_effect=Exception("LLM unavailable")
        )
        result = asyncio.run(
            suggest_gl_account("Software license", accounts, deps)
        )

    assert result is None  # Graceful degradation — no exception raised
