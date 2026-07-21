from __future__ import annotations

import pytest

from app.services.circuit_breaker import (
    CircuitBreaker,
    get_circuit_breaker,
    reset_all_circuit_breakers,
)

pytestmark = pytest.mark.unit


def test_breaker_opens_after_threshold_and_blocks() -> None:
    b = CircuitBreaker(failure_threshold=3, cooldown_seconds=30.0)
    assert b.allow() is True
    b.record_failure(now=100.0)
    b.record_failure(now=100.0)
    assert b.is_open is False
    b.record_failure(now=100.0)  # third failure trips it
    assert b.is_open is True
    assert b.allow(now=100.0) is False  # blocked during cooldown


def test_breaker_half_opens_after_cooldown() -> None:
    b = CircuitBreaker(failure_threshold=1, cooldown_seconds=10.0)
    b.record_failure(now=100.0)
    assert b.allow(now=105.0) is False  # still cooling down
    assert b.allow(now=111.0) is True  # cooldown elapsed → probe allowed


def test_breaker_success_resets() -> None:
    b = CircuitBreaker(failure_threshold=2, cooldown_seconds=10.0)
    b.record_failure(now=100.0)
    b.record_failure(now=100.0)
    assert b.is_open is True
    b.record_success()
    assert b.is_open is False
    assert b.allow() is True


def test_registry_returns_same_instance() -> None:
    reset_all_circuit_breakers()
    a = get_circuit_breaker("hermes:x")
    b = get_circuit_breaker("hermes:x")
    assert a is b
    reset_all_circuit_breakers()
    assert get_circuit_breaker("hermes:x") is not a
