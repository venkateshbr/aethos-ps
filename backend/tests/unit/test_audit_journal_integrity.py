"""Unit tests for the pre-deploy journal integrity audit (#372 AC 7)."""

from __future__ import annotations

import pytest

import scripts.audit_journal_integrity as audit_mod

pytestmark = pytest.mark.unit


class _Result:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _Query:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def select(self, _cols: str) -> _Query:
        return self

    def range(self, start: int, end: int) -> _Query:
        self._slice = self._rows[start : end + 1]
        return self

    def execute(self) -> _Result:
        return _Result(self._slice)


class _FakeDb:
    def __init__(self, entries: list[dict], lines: list[dict]) -> None:
        self._tables = {"journal_entries": entries, "journal_lines": lines}

    def table(self, name: str) -> _Query:
        return _Query(self._tables[name])


def _install(monkeypatch, entries, lines) -> None:
    monkeypatch.setattr(audit_mod, "_client", lambda: _FakeDb(entries, lines))


def test_audit_clean_returns_zero(monkeypatch, capsys) -> None:
    entries = [{"id": "e1", "tenant_id": "t1", "posted_at": "2026-07-01T00:00:00Z"}]
    lines = [
        {"journal_entry_id": "e1", "direction": "DR", "base_amount": "100.00"},
        {"journal_entry_id": "e1", "direction": "CR", "base_amount": "100.00"},
    ]
    _install(monkeypatch, entries, lines)
    assert audit_mod.audit() == 0
    assert "clean" in capsys.readouterr().out


def test_audit_flags_orphan_header(monkeypatch, capsys) -> None:
    entries = [{"id": "e2", "tenant_id": "t1", "posted_at": "2026-07-01T00:00:00Z"}]
    _install(monkeypatch, entries, [])  # posted header with no lines
    assert audit_mod.audit() == 1
    out = capsys.readouterr().out
    assert "Orphan headers (0 lines):       1" in out
    assert "ORPHAN" in out


def test_audit_flags_unbalanced_entry(monkeypatch, capsys) -> None:
    entries = [{"id": "e3", "tenant_id": "t1", "posted_at": "2026-07-01T00:00:00Z"}]
    lines = [
        {"journal_entry_id": "e3", "direction": "DR", "base_amount": "100.00"},
        {"journal_entry_id": "e3", "direction": "CR", "base_amount": "90.00"},
    ]
    _install(monkeypatch, entries, lines)
    assert audit_mod.audit() == 1
    assert "UNBALANCED" in capsys.readouterr().out


def test_audit_ignores_unposted_headers(monkeypatch, capsys) -> None:
    # posted_at is null → not in scope; its (missing) lines must not flag.
    entries = [{"id": "e4", "tenant_id": "t1", "posted_at": None}]
    _install(monkeypatch, entries, [])
    assert audit_mod.audit() == 0
    assert "audited: 0" in capsys.readouterr().out
