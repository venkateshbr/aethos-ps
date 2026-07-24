"""Unit tests for ACH bank routing/account validation (#404)."""

from __future__ import annotations

import pytest

from app.domain.bank_routing import (
    PLACEHOLDER_ROUTING,
    RoutingValidationError,
    is_valid_aba_routing,
    is_valid_ach_account,
    mask_account,
    require_valid_account,
    require_valid_routing,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "routing",
    [
        "021000021",   # JPMorgan Chase
        "011401533",   # a valid ABA
        "111000025",   # Federal Reserve Bank
        "021 000 021",  # separators tolerated
    ],
)
def test_valid_aba_routing(routing: str) -> None:
    assert is_valid_aba_routing(routing)


@pytest.mark.parametrize(
    "routing",
    [
        "021000020",   # last digit off → checksum fails
        "12345678",    # 8 digits
        "1234567890",  # 10 digits
        "02100002X",   # non-digit
        "",            # empty
    ],
)
def test_invalid_aba_routing(routing: str) -> None:
    assert not is_valid_aba_routing(routing)


def test_placeholder_routing_is_a_valid_aba() -> None:
    # The template file must be structurally parseable.
    assert is_valid_aba_routing(PLACEHOLDER_ROUTING)


@pytest.mark.parametrize("account", ["1", "12345678", "12345678901234567", "1234-5678"])
def test_valid_ach_account(account: str) -> None:
    assert is_valid_ach_account(account)


@pytest.mark.parametrize("account", ["", "123456789012345678", "12ab34", "abcd"])
def test_invalid_ach_account(account: str) -> None:
    assert not is_valid_ach_account(account)


def test_require_valid_routing_returns_normalized_or_raises() -> None:
    assert require_valid_routing("021 000 021") == "021000021"
    with pytest.raises(RoutingValidationError):
        require_valid_routing("021000020")


def test_require_valid_account_returns_normalized_or_raises() -> None:
    assert require_valid_account("1234-5678") == "12345678"
    with pytest.raises(RoutingValidationError):
        require_valid_account("abcd")


def test_mask_account_keeps_last_four() -> None:
    assert mask_account("12345678") == "****5678"
    assert mask_account("123") == "***"
    assert mask_account("1234-5678") == "****5678"
