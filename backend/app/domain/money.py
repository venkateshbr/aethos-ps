"""Money serialisation + arithmetic helpers — the one true API for money.

The Aethos rule is unambiguous (CLAUDE.md):
- Python: ``decimal.Decimal``, NEVER ``float``
- DB: ``NUMERIC(15,2)``
- JSON: string, exactly two decimal places

Every place where a money value crosses the API boundary MUST run through
``serialise_money``. This keeps Stripe metadata, NACHA exports, accounting
exports, and the frontend money pipe all reading exactly two decimal places.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

# Two-decimal quantum — the entire app pins money precision to this.
TWO_PLACES = Decimal("0.01")


def serialise_money(value: Decimal | str | int | float | None) -> str | None:
    """Render a money value as a canonical two-decimal-place string.

    ``None`` round-trips as ``None`` — used for nullable money columns
    (e.g. ``engagements.total_value``).

    Float input is accepted defensively but coerced via ``str()`` first so the
    binary-float representation never poisons the Decimal. Floats should not
    appear in our code paths; this is a guardrail, not an invitation.

    Raises ``InvalidOperation`` only when the input cannot be parsed as a
    Decimal at all (e.g. ``"abc"``).
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        amount = value
    else:
        amount = Decimal(str(value))
    return str(amount.quantize(TWO_PLACES))


# Backwards-compat alias — older code and Aksha's xfail spell it both ways.
serialize_money = serialise_money


def quantise_money(value: Decimal | str | int | float | None) -> Decimal | None:
    """Return a Decimal pinned to two decimal places, or None.

    Use this inside the service layer when you need to do further arithmetic
    after coercing an input. Use ``serialise_money`` at the API boundary.
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value.quantize(TWO_PLACES)
    return Decimal(str(value)).quantize(TWO_PLACES)


def parse_money(value: str | int | float | Decimal | None, *, default: str = "0") -> Decimal:
    """Parse a value to a quantised Decimal, falling back to ``default`` on error.

    Use inside the service layer when reading DB values where we want to be
    forgiving of stale rows that pre-date the quantization rule.
    """
    if value is None:
        return Decimal(default).quantize(TWO_PLACES)
    try:
        return Decimal(str(value)).quantize(TWO_PLACES)
    except (InvalidOperation, ValueError):
        return Decimal(default).quantize(TWO_PLACES)


__all__ = [
    "TWO_PLACES",
    "parse_money",
    "quantise_money",
    "serialise_money",
    "serialize_money",
]
