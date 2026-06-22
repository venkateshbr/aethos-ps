"""Tax ID / registration-number format validation (pure Python, no LLM).

Supported formats (day-1 launch markets — US, UK, AU, SG, IN):

  UK VAT:   GB + 9 digits  OR  GB + 12 digits
  AU ABN:   11 digits (no separators)
  SG UEN:   9 digits + uppercase letter  OR  T + 2 digits + 2 uppercase + 4 digits + uppercase
  IN GST:   15-char alphanumeric  (2 digits + 5 uppercase + 4 digits + 1 alpha + 1 alnum + Z + 1 alnum)
  US EIN:   2 digits + hyphen + 7 digits

Invalid format → adds a warning string (non-blocking) to the bill draft.
Country cross-check → if the vendor address country doesn't match the reg-number
  country prefix (e.g. UK address but EIN format), an inconsistency warning is added.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Country codes extracted from addresses (simple heuristics)
# ---------------------------------------------------------------------------

# Keyword → market code mapping for address cross-check.
# Keys are lowercase substrings that appear in country/region segments.
_ADDR_COUNTRY_MAP: dict[str, str] = {
    "united kingdom": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "northern ireland": "GB",
    "uk": "GB",
    "australia": "AU",
    "singapore": "SG",
    "india": "IN",
    "united states": "US",
    "usa": "US",
    "u.s.a": "US",
    "u.s.": "US",
}


def _infer_country_from_address(address: str | None) -> str | None:
    """Return a 2-letter market code inferred from a raw address string, or None."""
    if not address:
        return None
    lower = address.lower()
    for keyword, code in _ADDR_COUNTRY_MAP.items():
        if keyword in lower:
            return code
    return None


# ---------------------------------------------------------------------------
# Format patterns
# ---------------------------------------------------------------------------

# Each entry: (market_code, compiled_regex, human_label)
_FORMAT_RULES: list[tuple[str, re.Pattern[str], str]] = [
    # UK VAT: GB followed by 9 or 12 digits
    ("GB", re.compile(r"^GB\d{9}(\d{3})?$"), "UK VAT (GB + 9 or 12 digits)"),
    # AU ABN: exactly 11 digits
    ("AU", re.compile(r"^\d{11}$"), "AU ABN (11 digits)"),
    # SG UEN: 9 digits + uppercase letter  OR  T + 2 digits + 2 uppercase + 4 digits + uppercase
    ("SG", re.compile(r"^(\d{9}[A-Z]|T\d{2}[A-Z]{2}\d{4}[A-Z])$"), "SG UEN"),
    # IN GST: 15 chars  — 2 digits + 5 upper + 4 digits + alpha + alnum + Z + alnum
    ("IN", re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][0-9A-Z]Z[0-9A-Z]$"), "IN GST (15 chars)"),
    # US EIN: 2 digits + hyphen + 7 digits
    ("US", re.compile(r"^\d{2}-\d{7}$"), "US EIN (XX-XXXXXXX)"),
]

# Map market code → human label for cross-check messages
_MARKET_LABEL: dict[str, str] = {
    "GB": "UK",
    "AU": "AU",
    "SG": "SG",
    "IN": "IN",
    "US": "US",
}


def _detect_reg_market(reg_number: str) -> str | None:
    """Return the market code (e.g. 'GB') if reg_number matches a known format."""
    for market, pattern, _ in _FORMAT_RULES:
        if pattern.match(reg_number):
            return market
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_tax_id(
    reg_number: str | None,
    vendor_address: str | None = None,
) -> list[str]:
    """Validate a tax / registration number and return a list of warning strings.

    Warnings are non-blocking: callers add them to ``BillDraft.tax_id_warnings``
    and surface them as advisory flags in the HITL card.

    Args:
        reg_number: The raw registration/tax number extracted from the bill.
            May include spaces or hyphens. If None or empty, returns no warnings.
        vendor_address: Raw address text. Used for country cross-check only.

    Returns:
        A (possibly empty) list of human-readable warning strings.
    """
    if not reg_number:
        return []

    # Normalise: strip whitespace; keep other characters as-is for pattern matching
    normalised = reg_number.strip().replace(" ", "")

    if not normalised:
        return []

    warnings: list[str] = []

    # --- 1. Format check ---
    matched_market = _detect_reg_market(normalised)
    if matched_market is None:
        warnings.append(
            f"Tax ID {reg_number!r} does not match any known format "
            "(GB VAT, AU ABN, SG UEN, IN GST, US EIN). Please verify."
        )

    # --- 2. Country cross-check ---
    if matched_market is not None and vendor_address:
        addr_market = _infer_country_from_address(vendor_address)
        if addr_market is not None and addr_market != matched_market:
            reg_label = _MARKET_LABEL.get(matched_market, matched_market)
            addr_label = _MARKET_LABEL.get(addr_market, addr_market)
            warnings.append(
                f"Mismatch: vendor address suggests {addr_label} but "
                f"tax ID format is {reg_label} ({reg_number!r}). Please verify."
            )

    return warnings
