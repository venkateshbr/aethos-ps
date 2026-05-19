"""Pytest fixtures for Aethos PS backend tests.

Skeleton. Real fixtures (DB, HTTP client, agent mocks) wired by Karya/Sthira
as the backend lands. Helpers here are pure-Python so the property + unit
suites can run before any of the rest exists.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

import pytest

# ---------------------------------------------------------------------------
# Money helpers (pure-Python; safe to use before the domain layer exists)
# ---------------------------------------------------------------------------

Direction = Literal["DR", "CR"]


@dataclass(frozen=True)
class JournalLine:
    direction: Direction
    account: str
    amount: Decimal
    currency: str = "USD"
    base_amount: Decimal | None = None  # tenant base; defaults to amount for single-currency

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("amount must be Decimal")
        if self.amount.as_tuple().exponent < -2:
            raise ValueError("amount must have at most 2 decimal places")
        if self.base_amount is None:
            object.__setattr__(self, "base_amount", self.amount)


@dataclass(frozen=True)
class JournalEntry:
    lines: list[JournalLine] = field(default_factory=list)

    @property
    def debits(self) -> Decimal:
        return sum((l.base_amount for l in self.lines if l.direction == "DR"), Decimal("0"))

    @property
    def credits(self) -> Decimal:
        return sum((l.base_amount for l in self.lines if l.direction == "CR"), Decimal("0"))

    def is_balanced(self, fx_tolerance: Decimal = Decimal("0.01")) -> bool:
        return abs(self.debits - self.credits) <= fx_tolerance


@pytest.fixture
def make_journal_entry():
    """Build a JournalEntry from list of (direction, account, amount) tuples."""

    def _builder(lines: list[tuple[Direction, str, str | Decimal]]) -> JournalEntry:
        return JournalEntry(
            lines=[
                JournalLine(
                    direction=d,
                    account=acct,
                    amount=Decimal(str(amt)),
                )
                for (d, acct, amt) in lines
            ]
        )

    return _builder


# ---------------------------------------------------------------------------
# Tenant scaffolding (deterministic IDs for cleanup)
# ---------------------------------------------------------------------------


@pytest.fixture
def test_run_id() -> str:
    """Deterministic run identifier that prefixes all test artifacts."""
    return "run-" + uuid.uuid4().hex[:8]


@pytest.fixture
def test_tenant_id(test_run_id: str) -> str:
    return f"test-tenant-{test_run_id}"


# ---------------------------------------------------------------------------
# Agent mock scaffolding
# ---------------------------------------------------------------------------


@dataclass
class AgentMockOutput:
    """Stand-in for a PydanticAI agent output until the agents land."""

    structured: dict
    confidence: float
    hitl_required: bool = False
    suspected_injection: bool = False


@pytest.fixture
def agent_mock_output():
    def _make(**kwargs) -> AgentMockOutput:
        kwargs.setdefault("structured", {})
        kwargs.setdefault("confidence", 0.9)
        return AgentMockOutput(**kwargs)

    return _make


# ---------------------------------------------------------------------------
# HTTP client (placeholder — wired when api/ exists)
# ---------------------------------------------------------------------------


@pytest.fixture
def api_client():
    """Real httpx client against running API.

    Skeleton: returns a marker that tests `xfail` on until backend boots.
    """
    pytest.xfail("api_client not yet wired — backend not bootstrapped")
