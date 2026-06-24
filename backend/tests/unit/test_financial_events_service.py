"""Unit tests for immutable financial event log reads."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

from app.services.financial_events_service import FinancialEventsService

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-fin-events-001"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = list(rows)
        self._filters: list[tuple[str, Any]] = []
        self._limit: int | None = None
        self._offset = 0
        self._order_by: str | None = None
        self._order_desc = False

    def select(self, _columns: str) -> _Query:
        return self

    def eq(self, field: str, value: Any) -> _Query:
        self._filters.append((field, value))
        return self

    def order(self, field: str, desc: bool = False) -> _Query:
        self._order_by = field
        self._order_desc = desc
        return self

    def limit(self, value: int) -> _Query:
        self._limit = value
        return self

    def offset(self, value: int) -> _Query:
        self._offset = value
        return self

    def execute(self) -> _Result:
        rows = [row for row in self._rows if self._matches(row)]
        if self._order_by:
            rows.sort(key=lambda row: row.get(self._order_by) or "", reverse=self._order_desc)
        if self._offset:
            rows = rows[self._offset :]
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Result(rows)

    def _matches(self, row: dict[str, Any]) -> bool:
        return all(row.get(field) == value for field, value in self._filters)


class _Db:
    def __init__(self) -> None:
        self.rows = [
            _event(
                "event-older",
                event_type="journal_entry.posted",
                entity_type="journal_entry",
                entity_id="journal-1",
                created_at="2026-06-21T10:00:00+00:00",
                previous_event_hash=None,
            ),
            _event(
                "event-newer",
                event_type="period.locked",
                entity_type="period_lock",
                entity_id="lock-1",
                created_at="2026-06-22T10:00:00+00:00",
                previous_event_hash="hash-older",
            ),
        ]

    def table(self, name: str) -> _Query:
        assert name == "financial_events"
        return _Query(self.rows)


def _event(
    event_id: str,
    *,
    event_type: str,
    entity_type: str,
    entity_id: str,
    created_at: str,
    previous_event_hash: str | None,
) -> dict[str, Any]:
    return {
        "id": event_id,
        "tenant_id": TENANT_ID,
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "source_type": entity_type,
        "source_id": entity_id,
        "actor_user_id": "user-1",
        "actor_role": None,
        "action": event_type.split(".")[-1],
        "before_state": {},
        "after_state": {"id": entity_id},
        "metadata": {},
        "idempotency_key": f"{event_type}:{entity_id}",
        "previous_event_hash": previous_event_hash,
        "event_hash": f"hash-{event_id}",
        "created_at": created_at,
    }


def test_list_events_returns_newest_first() -> None:
    result = FinancialEventsService(_Db(), TENANT_ID).list_events()  # type: ignore[arg-type]

    assert result.total == 2
    assert [event.id for event in result.items] == ["event-newer", "event-older"]
    assert result.items[0].previous_event_hash == "hash-older"


def test_list_events_filters_by_event_and_entity() -> None:
    result = FinancialEventsService(_Db(), TENANT_ID).list_events(  # type: ignore[arg-type]
        event_type="journal_entry.posted",
        entity_type="journal_entry",
        entity_id="journal-1",
    )

    assert result.total == 1
    assert result.items[0].id == "event-older"
    assert result.items[0].event_type == "journal_entry.posted"


def test_export_events_csv_includes_hash_chain_columns() -> None:
    raw = FinancialEventsService(_Db(), TENANT_ID).export_events_csv(  # type: ignore[arg-type]
        event_type="period.locked"
    )

    rows = list(csv.DictReader(StringIO(raw.decode("utf-8"))))
    assert len(rows) == 1
    row = rows[0]
    assert row["event_type"] == "period.locked"
    assert row["entity_type"] == "period_lock"
    assert row["previous_event_hash"] == "hash-older"
    assert row["event_hash"] == "hash-event-newer"
    assert row["after_state_json"] == '{"id":"lock-1"}'


def test_financial_events_migration_defends_immutability() -> None:
    migration = (
        Path(__file__).parents[2]
        / "supabase"
        / "migrations"
        / "0039_financial_event_log.sql"
    ).read_text()

    assert "BEFORE UPDATE ON financial_events" in migration
    assert "BEFORE DELETE ON financial_events" in migration
    assert "financial_events is immutable" in migration
