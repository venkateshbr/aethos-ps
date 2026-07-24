"""Bank routing / account validation for ACH (NACHA) bill-payment exports (#404).

Pure, dependency-free validators so the bill-payment export path can *validate*
operator-supplied bank data and never emit a structurally-invalid instruction.
This module intentionally holds no storage — raw bank account numbers are never
persisted by the payments service (Prahari gate); these helpers only validate and
mask values that pass through at export time.
"""

from __future__ import annotations

import re

_DIGITS = re.compile(r"^\d+$")


class RoutingValidationError(ValueError):
    """Raised when a routing or account number fails validation."""


def normalize_digits(value: str) -> str:
    """Strip spaces and dashes commonly present in printed routing/account numbers."""
    return re.sub(r"[ \-]", "", value or "")


def is_valid_aba_routing(routing: str) -> bool:
    """Validate a US ABA routing number: 9 digits with the ABA check digit.

    Checksum: 3*(d1+d4+d7) + 7*(d2+d5+d8) + 1*(d3+d6+d9) ≡ 0 (mod 10).
    """
    digits = normalize_digits(routing)
    if len(digits) != 9 or not _DIGITS.match(digits):
        return False
    d = [int(c) for c in digits]
    checksum = (
        3 * (d[0] + d[3] + d[6])
        + 7 * (d[1] + d[4] + d[7])
        + 1 * (d[2] + d[5] + d[8])
    )
    return checksum % 10 == 0


def is_valid_ach_account(account: str) -> bool:
    """Validate a US ACH DFI account number: 1-17 characters, digits only.

    The NACHA DFI Account Number field is 17 chars; account numbers here are
    numeric. (Alphanumeric accounts exist on some rails but are out of scope for
    the US ACH export.)
    """
    digits = normalize_digits(account)
    return bool(digits) and len(digits) <= 17 and bool(_DIGITS.match(digits))


def require_valid_routing(routing: str) -> str:
    """Return the normalized routing number or raise RoutingValidationError."""
    normalized = normalize_digits(routing)
    if not is_valid_aba_routing(normalized):
        raise RoutingValidationError(
            "Invalid ABA routing number (must be 9 digits with a valid ABA check digit)"
        )
    return normalized


def require_valid_account(account: str) -> str:
    """Return the normalized account number or raise RoutingValidationError."""
    normalized = normalize_digits(account)
    if not is_valid_ach_account(normalized):
        raise RoutingValidationError(
            "Invalid ACH account number (must be 1-17 digits)"
        )
    return normalized


def mask_account(account: str) -> str:
    """Mask all but the last 4 digits for display/logging (never store full)."""
    digits = normalize_digits(account)
    if len(digits) <= 4:
        return "*" * len(digits)
    return "*" * (len(digits) - 4) + digits[-4:]


# The placeholder routing used in template exports — a real, checksum-valid ABA
# number (021000021, JPMorgan Chase) so the template file is structurally parseable,
# but it is NOT the firm's funding account. A template must be completed by the
# operator (or confirmed complete) before the batch can be marked sent to bank.
PLACEHOLDER_ROUTING = "021000021"
