"""Unit tests for app.domain.tax_id_validator.

Pure-Python, no I/O, no mocks needed.

Covers:
- Valid formats for all 5 launch markets (UK/AU/SG/IN/US)
- Invalid-format detection
- Country cross-check (address vs reg-number format)
- Edge cases: None, empty string, whitespace
"""

from __future__ import annotations

import pytest

from app.domain.tax_id_validator import validate_tax_id

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Valid formats — expect zero warnings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("reg", [
    "GB123456789",          # UK VAT 9-digit
    "GB123456789012",       # UK VAT 12-digit
])
def test_uk_vat_valid(reg: str) -> None:
    assert validate_tax_id(reg) == [], f"Expected no warnings for valid UK VAT: {reg}"


def test_au_abn_valid() -> None:
    assert validate_tax_id("12345678901") == []   # 11 digits


@pytest.mark.parametrize("reg", [
    "123456789A",           # SG UEN 9 digits + letter
    "T12AB1234C",           # SG UEN T-prefix format
])
def test_sg_uen_valid(reg: str) -> None:
    assert validate_tax_id(reg) == [], f"Expected no warnings for valid SG UEN: {reg}"


def test_in_gst_valid() -> None:
    # 2 digits + 5 upper + 4 digits + alpha + alnum + Z + alnum
    assert validate_tax_id("27AAPFU0939F1Z5") == []


def test_us_ein_valid() -> None:
    assert validate_tax_id("12-3456789") == []


# ---------------------------------------------------------------------------
# Invalid formats — expect a warning
# ---------------------------------------------------------------------------


def test_invalid_format_produces_warning() -> None:
    warnings = validate_tax_id("INVALID123")
    assert len(warnings) == 1
    assert "does not match any known format" in warnings[0]


def test_random_digits_invalid() -> None:
    warnings = validate_tax_id("9999999")
    assert warnings  # 7 digits matches none of the 5 formats


def test_uk_vat_wrong_digit_count_invalid() -> None:
    # GB + 8 digits — too short for UK VAT
    warnings = validate_tax_id("GB12345678")
    assert warnings


def test_us_ein_missing_hyphen_invalid() -> None:
    warnings = validate_tax_id("123456789")
    assert warnings  # 9 digits without hyphen — not EIN format


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_none_returns_no_warnings() -> None:
    assert validate_tax_id(None) == []


def test_empty_string_returns_no_warnings() -> None:
    assert validate_tax_id("") == []


def test_whitespace_only_returns_no_warnings() -> None:
    # The validator strips whitespace; "" after strip → early exit
    assert validate_tax_id("   ") == []


def test_valid_reg_with_surrounding_whitespace() -> None:
    # Leading/trailing whitespace should be stripped before matching
    warnings = validate_tax_id("  12-3456789  ")
    assert warnings == [], "Whitespace-padded EIN should still validate"


# ---------------------------------------------------------------------------
# Country cross-check
# ---------------------------------------------------------------------------


def test_cross_check_uk_address_uk_vat_no_warning() -> None:
    warnings = validate_tax_id("GB123456789", vendor_address="12 Baker St, London, United Kingdom")
    assert warnings == []


def test_cross_check_uk_address_us_ein_warns() -> None:
    warnings = validate_tax_id("12-3456789", vendor_address="100 Main St, London, United Kingdom")
    assert len(warnings) == 1
    assert "Mismatch" in warnings[0]
    assert "UK" in warnings[0]
    assert "US" in warnings[0]


def test_cross_check_au_address_au_abn_no_warning() -> None:
    warnings = validate_tax_id("12345678901", vendor_address="1 George St, Sydney, Australia")
    assert warnings == []


def test_cross_check_sg_address_in_gst_warns() -> None:
    warnings = validate_tax_id("27AAPFU0939F1Z5", vendor_address="1 Raffles Place, Singapore")
    assert len(warnings) == 1
    assert "Mismatch" in warnings[0]


def test_cross_check_unknown_address_country_no_warning() -> None:
    # If we can't infer address country → no cross-check warning
    warnings = validate_tax_id("GB123456789", vendor_address="Some mysterious location")
    assert warnings == []


def test_cross_check_no_address_no_warning() -> None:
    warnings = validate_tax_id("GB123456789", vendor_address=None)
    assert warnings == []


# ---------------------------------------------------------------------------
# Multiple warnings (bad format + cross-check can't both fire; only 1 at most
# because cross-check requires format to match first)
# ---------------------------------------------------------------------------


def test_invalid_format_no_cross_check_warning() -> None:
    # If format is invalid, we don't run cross-check
    warnings = validate_tax_id("BADREG", vendor_address="London, United Kingdom")
    # Expect exactly 1 warning (format) — no cross-check because format didn't match
    assert len(warnings) == 1
    assert "does not match any known format" in warnings[0]
