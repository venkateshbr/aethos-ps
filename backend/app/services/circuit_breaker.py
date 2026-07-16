"""In-process circuit breaker to fast-fail a flapping upstream.

When Hermes is down, retrying every chat turn makes each request pay the connect
timeout before falling back to the Basic runtime. A breaker trips after a few
consecutive failures and then fast-fails (straight to fallback) for a cooldown
window, with a single half-open probe afterwards to detect recovery.

Scope is intentionally per-process and in-memory: it protects a single API
worker's latency under an outage. It is not a distributed breaker.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class CircuitBreaker:
    """A minimal closed → open → half-open breaker."""

    failure_threshold: int = 5
    cooldown_seconds: float = 30.0
    _consecutive_failures: int = 0
    _opened_at: float | None = None

    def allow(self, *, now: float | None = None) -> bool:
        """True when a call may proceed (closed, or half-open probe)."""
        if self._opened_at is None:
            return True
        current = time.monotonic() if now is None else now
        # Cooldown elapsed → allow a single probe (half-open).
        return current - self._opened_at >= self.cooldown_seconds

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._opened_at = None

    def record_failure(self, *, now: float | None = None) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self._opened_at = time.monotonic() if now is None else now

    @property
    def is_open(self) -> bool:
        return self._opened_at is not None

    def reset(self) -> None:
        self._consecutive_failures = 0
        self._opened_at = None


_registry: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    *,
    failure_threshold: int = 5,
    cooldown_seconds: float = 30.0,
) -> CircuitBreaker:
    """Return the process-wide breaker for ``name``, creating it on first use."""
    breaker = _registry.get(name)
    if breaker is None:
        breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            cooldown_seconds=cooldown_seconds,
        )
        _registry[name] = breaker
    return breaker


def reset_all_circuit_breakers() -> None:
    """Test helper: clear breaker state between tests."""
    _registry.clear()
