"""Strict ISO-style currency-code normalization for financial write paths."""

from __future__ import annotations

import re

_CURRENCY_CODE = re.compile(r"[A-Z]{3}")


def normalise_currency_code(value: object) -> str:
    """Return an uppercase three-ASCII-letter code or raise ``ValueError``."""
    currency = str(value or "").strip().upper()
    if _CURRENCY_CODE.fullmatch(currency) is None:
        raise ValueError("Currency must be a three-letter ISO code")
    return currency
