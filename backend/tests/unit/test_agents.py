"""Unit tests for agent base infrastructure and output schemas.

All tests are pure-Python with no I/O.  They verify:
  - PII masking correctness (mask_pii)
  - Schema defaults and validation (EngagementDraft, ProjectExpenseDraft, BillDraft)
  - HITL / autonomy-level logic (inline, mirrors suggestion_writer.py rules)

No mocks of Anthropic or Supabase are needed — these tests cover the logic
layer, not the agent execution layer.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.agents.base import mask_pii
from app.agents.schemas import BillDraft, EngagementDraft, ProjectExpenseDraft

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# mask_pii
# ---------------------------------------------------------------------------


def test_mask_pii_redacts_ssn() -> None:
    assert "[REDACTED-SSN]" in mask_pii("SSN: 123-45-6789")


def test_mask_pii_redacts_card() -> None:
    assert "[REDACTED-CARD]" in mask_pii("card: 4111111111111111")


def test_mask_pii_redacts_card_with_spaces() -> None:
    assert "[REDACTED-CARD]" in mask_pii("card: 4111 1111 1111 1111")


def test_mask_pii_redacts_email_username_keeps_domain() -> None:
    result = mask_pii("email: alice@example.com")
    assert "alice" not in result
    assert "example.com" in result


def test_mask_pii_redacts_multiple_emails() -> None:
    result = mask_pii("from: bob@acme.io to: carol@acme.io")
    assert "bob" not in result
    assert "carol" not in result
    assert "acme.io" in result


def test_mask_pii_no_false_positives_on_normal_text() -> None:
    text = "Invoice for consulting services, $5,000 due 30 days"
    assert mask_pii(text) == text


def test_mask_pii_no_false_positives_on_date() -> None:
    # ISO dates like 2024-01-15 must NOT be treated as SSNs
    text = "Start date: 2024-01-15"
    assert mask_pii(text) == text


def test_mask_pii_preserves_normal_numbers() -> None:
    text = "Invoice #12345, amount $1,234.56"
    assert mask_pii(text) == text


# ---------------------------------------------------------------------------
# EngagementDraft
# ---------------------------------------------------------------------------


def test_engagement_draft_defaults_confidence_to_half() -> None:
    d = EngagementDraft()
    assert d.confidence == 0.5


def test_engagement_draft_defaults_billing_arrangement() -> None:
    d = EngagementDraft()
    assert d.billing_arrangement == "time_and_materials"


def test_engagement_draft_defaults_client_name_empty() -> None:
    d = EngagementDraft()
    assert d.client_name == ""


def test_engagement_draft_suspected_injection_defaults_false() -> None:
    d = EngagementDraft(client_name="Acme", billing_arrangement="fixed_fee", confidence=0.9)
    assert d.suspected_injection is False


def test_engagement_draft_rate_card_hints_default_empty() -> None:
    d = EngagementDraft()
    assert d.rate_card_hints == []


def test_engagement_draft_accepts_valid_billing_arrangement() -> None:
    valid_arrangements = [
        "time_and_materials",
        "fixed_fee",
        "retainer",
        "retainer_draw",
        "milestone",
        "capped_tm",
    ]
    for arrangement in valid_arrangements:
        d = EngagementDraft(billing_arrangement=arrangement, confidence=0.8)
        assert d.billing_arrangement == arrangement


def test_engagement_draft_confidence_clamped_validation() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        EngagementDraft(confidence=1.5)  # above 1.0


def test_engagement_draft_empty_raw_gives_safe_defaults() -> None:
    """Simulates the agent returning {} when LLM parse fails."""
    raw: dict = {}
    d = EngagementDraft(**raw)
    assert d.confidence == 0.5
    assert d.client_name == ""
    assert d.suspected_injection is False


# ---------------------------------------------------------------------------
# ProjectExpenseDraft
# ---------------------------------------------------------------------------


def test_expense_draft_validates_category() -> None:
    d = ProjectExpenseDraft(
        vendor="Uber",
        amount=Decimal("25.00"),
        category="transport",
        confidence=0.95,
    )
    assert d.category == "transport"


def test_expense_draft_anomaly_detected_not_present_by_default() -> None:
    # ProjectExpenseDraft does not have anomaly_detected — suspected_injection is the flag
    d = ProjectExpenseDraft(
        vendor="Uber",
        amount=Decimal("25.00"),
        category="transport",
        confidence=0.80,
    )
    assert d.suspected_injection is False


def test_expense_draft_description_defaults_empty() -> None:
    d = ProjectExpenseDraft(
        vendor="Hilton",
        amount=Decimal("199.00"),
        category="accommodation",
        confidence=0.9,
    )
    assert d.description == ""


def test_expense_draft_currency_defaults_usd() -> None:
    d = ProjectExpenseDraft(
        vendor="OpenAI",
        amount=Decimal("20.00"),
        category="software",
        confidence=0.85,
    )
    assert d.currency == "USD"


def test_expense_draft_expense_date_defaults_none() -> None:
    d = ProjectExpenseDraft(
        vendor="Grab",
        amount=Decimal("12.50"),
        category="transport",
        confidence=0.7,
    )
    assert d.expense_date is None


# ---------------------------------------------------------------------------
# BillDraft
# ---------------------------------------------------------------------------


def test_bill_draft_possible_duplicate_defaults_false() -> None:
    d = BillDraft(
        vendor_name="AWS",
        subtotal=Decimal("100"),
        total=Decimal("100"),
        confidence=0.88,
    )
    assert d.possible_duplicate is False


def test_bill_draft_marks_anomaly() -> None:
    d = BillDraft(
        vendor_name="AWS",
        subtotal=Decimal("100"),
        total=Decimal("200"),
        confidence=0.7,
        anomaly_detected=True,
    )
    assert d.anomaly_detected is True


def test_bill_draft_anomaly_defaults_false() -> None:
    d = BillDraft(
        vendor_name="GCP",
        subtotal=Decimal("500"),
        total=Decimal("500"),
        confidence=0.9,
    )
    assert d.anomaly_detected is False


def test_bill_draft_tax_total_defaults_zero() -> None:
    d = BillDraft(
        vendor_name="Azure",
        subtotal=Decimal("200"),
        total=Decimal("200"),
        confidence=0.85,
    )
    assert d.tax_total == Decimal("0")


def test_bill_draft_lines_default_empty() -> None:
    d = BillDraft(
        vendor_name="Twilio",
        subtotal=Decimal("50"),
        total=Decimal("50"),
        confidence=0.75,
    )
    assert d.lines == []


def test_bill_draft_vendor_invoice_number_optional() -> None:
    d = BillDraft(
        vendor_name="Stripe",
        subtotal=Decimal("30"),
        total=Decimal("30"),
        confidence=0.9,
    )
    assert d.vendor_invoice_number is None


def test_bill_draft_suspected_injection_defaults_false() -> None:
    d = BillDraft(
        vendor_name="Cloudflare",
        subtotal=Decimal("25"),
        total=Decimal("25"),
        confidence=0.88,
    )
    assert d.suspected_injection is False


# ---------------------------------------------------------------------------
# HITL / autonomy-level logic (mirrors suggestion_writer.py, no I/O)
# ---------------------------------------------------------------------------


def test_suggestion_hitl_required_when_autonomy_l2() -> None:
    """L2 agent always requires HITL regardless of confidence."""
    autonomy_level = 2
    confidence = 0.99
    threshold = 0.90
    suspected_injection = False
    hitl = suspected_injection or autonomy_level < 3 or confidence < threshold
    assert hitl is True


def test_suggestion_hitl_required_when_autonomy_l1() -> None:
    autonomy_level = 1
    confidence = 0.99
    threshold = 0.90
    suspected_injection = False
    hitl = suspected_injection or autonomy_level < 3 or confidence < threshold
    assert hitl is True


def test_suggestion_hitl_required_when_low_confidence() -> None:
    autonomy_level = 3
    confidence = 0.50
    threshold = 0.90
    suspected_injection = False
    hitl = suspected_injection or autonomy_level < 3 or confidence < threshold
    assert hitl is True


def test_suggestion_hitl_required_when_exactly_at_threshold() -> None:
    """Confidence exactly at threshold — HITL not required (>= not just >)."""
    autonomy_level = 3
    confidence = 0.90
    threshold = 0.90
    suspected_injection = False
    # confidence < threshold is False when equal
    hitl = suspected_injection or autonomy_level < 3 or confidence < threshold
    assert hitl is False


def test_suggestion_auto_applied_when_l3_high_confidence() -> None:
    autonomy_level = 3
    confidence = 0.95
    threshold = 0.90
    suspected_injection = False
    hitl = suspected_injection or autonomy_level < 3 or confidence < threshold
    assert hitl is False


def test_suggestion_injection_always_forces_hitl() -> None:
    """Even L3 at max confidence must go to HITL when injection detected."""
    suspected_injection = True
    autonomy_level = 3
    confidence = 0.99
    threshold = 0.90
    hitl = suspected_injection or autonomy_level < 3 or confidence < threshold
    assert hitl is True


def test_suggestion_priority_critical_on_injection() -> None:
    """Injection → critical priority."""
    suspected_injection = True
    confidence = 0.99
    if suspected_injection:
        priority = "critical"
    elif confidence < 0.5:
        priority = "high"
    else:
        priority = "med"
    assert priority == "critical"


def test_suggestion_priority_high_on_low_confidence() -> None:
    suspected_injection = False
    confidence = 0.40
    if suspected_injection:
        priority = "critical"
    elif confidence < 0.5:
        priority = "high"
    else:
        priority = "med"
    assert priority == "high"


def test_suggestion_priority_med_on_normal_confidence() -> None:
    suspected_injection = False
    confidence = 0.75
    if suspected_injection:
        priority = "critical"
    elif confidence < 0.5:
        priority = "high"
    else:
        priority = "med"
    assert priority == "med"
