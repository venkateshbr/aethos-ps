"""Unit tests for atomic/idempotent journal posting (ADR 0001 / #390 / LR-08)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

import app.agents.accounting_guardian as guardian
from app.domain.journal_helper import (
    JournalLineSpec,
    _journal_idempotency_key,
    post_journal,
)

pytestmark = pytest.mark.unit


def _lines(amount: str = "100.00") -> list[JournalLineSpec]:
    return [
        JournalLineSpec(direction="DR", account_code="1200", account_id="acc-ar",
                        amount=Decimal(amount), description="AR"),
        JournalLineSpec(direction="CR", account_code="4000", account_id="acc-rev",
                        amount=Decimal(amount), description="Revenue"),
    ]


class _Exec:
    def __init__(self, data: Any):
        self._data = data

    def execute(self) -> Any:
        return type("Resp", (), {"data": self._data})()


class _RpcOnlyDb:
    """DB double that only supports .rpc().execute(); .table() would signal the
    old, non-atomic two-insert path still being used."""

    def __init__(self) -> None:
        self.rpc_calls: list[tuple[str, dict[str, Any]]] = []

    def rpc(self, name: str, params: dict[str, Any]) -> _Exec:
        self.rpc_calls.append((name, params))
        entry = {
            "id": "je-123",
            "entry_number": params["p_entry"]["entry_number"],
            "idempotency_key": params["p_idempotency_key"],
        }
        return _Exec({"entry": entry, "idempotent_hit": False})

    def table(self, *_a, **_k):  # pragma: no cover - guard
        raise AssertionError("post_journal must post via the atomic RPC, not table().insert()")


def test_idempotency_key_is_deterministic_and_content_sensitive() -> None:
    lines_a = [
        {"account_id": "a", "direction": "DR", "base_amount": "100.00", "currency": "USD"},
        {"account_id": "b", "direction": "CR", "base_amount": "100.00", "currency": "USD"},
    ]
    k1 = _journal_idempotency_key("t1", "invoice", "inv-1", "2026-07-01", "June invoice", lines_a)
    # Same content, lines in different order → same key (order-independent).
    k2 = _journal_idempotency_key("t1", "invoice", "inv-1", "2026-07-01", "June invoice", list(reversed(lines_a)))
    assert k1 == k2
    assert k1.startswith("je:")

    # Different amounts (e.g. bill approval vs settlement) → different key.
    lines_b = [
        {"account_id": "a", "direction": "DR", "base_amount": "200.00", "currency": "USD"},
        {"account_id": "b", "direction": "CR", "base_amount": "200.00", "currency": "USD"},
    ]
    assert _journal_idempotency_key("t1", "invoice", "inv-1", "2026-07-01", "June invoice", lines_b) != k1
    # Different reference → different key.
    assert _journal_idempotency_key("t1", "invoice", "inv-2", "2026-07-01", "June invoice", lines_a) != k1


def test_post_journal_uses_atomic_rpc_and_returns_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guardian, "validate_journal", lambda *a, **k: {"action": "post"})
    db = _RpcOnlyDb()

    je = post_journal(
        db, "tenant-1", "user-1", "Invoice INV-1 posted",
        "2026-07-01", "invoice", "inv-1", _lines(),
    )

    assert je["id"] == "je-123"
    assert len(db.rpc_calls) == 1
    name, params = db.rpc_calls[0]
    assert name == "post_journal_entry"
    assert params["p_idempotency_key"].startswith("je:")
    assert len(params["p_lines"]) == 2
    # lines carry no journal_entry_id (the RPC assigns it atomically)
    assert all("journal_entry_id" not in ln for ln in params["p_lines"])


def test_post_journal_key_is_stable_across_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guardian, "validate_journal", lambda *a, **k: {"action": "post"})
    db1, db2 = _RpcOnlyDb(), _RpcOnlyDb()
    args = (("tenant-1", "user-1", "same post", "2026-07-01", "payment", "pay-9"), _lines())
    post_journal(db1, *args[0], args[1])
    post_journal(db2, *args[0], args[1])
    # Same logical post → identical idempotency key → RPC dedupes to one entry.
    assert db1.rpc_calls[0][1]["p_idempotency_key"] == db2.rpc_calls[0][1]["p_idempotency_key"]


def test_guardian_rejection_still_blocks_posting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guardian, "validate_journal", lambda *a, **k: {"action": "reject", "reason": "imbalanced"})
    db = _RpcOnlyDb()
    with pytest.raises(ValueError, match="imbalanced"):
        post_journal(db, "tenant-1", "user-1", "bad", "2026-07-01", "manual", "m-1", _lines())
    assert db.rpc_calls == []  # never reached the RPC
