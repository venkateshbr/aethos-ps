from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from scripts import seed_demo

pytestmark = pytest.mark.unit


class _Query:
    def __init__(self, table: str, updates: list[tuple[str, dict[str, object]]]) -> None:
        self.table = table
        self.updates = updates
        self.patch: dict[str, object] | None = None

    def select(self, *_args: object) -> _Query:
        return self

    def eq(self, *_args: object) -> _Query:
        return self

    def in_(self, *_args: object) -> _Query:
        return self

    def update(self, patch: dict[str, object]) -> _Query:
        self.patch = patch
        return self

    def execute(self) -> SimpleNamespace:
        if self.patch is not None:
            self.updates.append((self.table, self.patch))
            return SimpleNamespace(data=[self.patch])
        if self.table == "invoices":
            return SimpleNamespace(data=[{
                "id": "invoice-1",
                "total": "100.00",
                "currency": "GBP",
                "invoice_number": "INV-TEST",
                "issue_date": "2026-06-15",
            }])
        if self.table == "accounts":
            return SimpleNamespace(data=[
                {"id": "ar-account", "code": "1200"},
                {"id": "revenue-account", "code": "4000"},
            ])
        raise AssertionError(f"Unexpected table: {self.table}")


class _Db:
    def __init__(self) -> None:
        self.updates: list[tuple[str, dict[str, object]]] = []

    def table(self, name: str) -> _Query:
        return _Query(name, self.updates)


def test_seed_invoice_approval_uses_atomic_journal_poster(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    post_journal = MagicMock(return_value={"id": "journal-1"})
    monkeypatch.setattr(seed_demo, "post_journal", post_journal, raising=False)
    db = _Db()

    seed_demo._approve_invoice(db, "tenant-1", "invoice-1")  # type: ignore[arg-type]

    post_journal.assert_called_once()
    kwargs = post_journal.call_args.kwargs
    assert kwargs["tenant_id"] == "tenant-1"
    assert kwargs["reference_type"] == "invoice"
    assert kwargs["reference_id"] == "invoice-1"
    assert len(kwargs["lines"]) == 2
    assert db.updates == [("invoices", {"status": "approved"})]
