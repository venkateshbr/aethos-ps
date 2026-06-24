"""Unit tests for provider webhook audit event reads."""

from __future__ import annotations

from typing import Any

import pytest

from app.services.webhook_events_service import WebhookEventsService

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-webhook-events-001"


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
                "webhook-older",
                provider_event_id="evt_older",
                event_type="invoice.paid",
                processed_at="2026-06-21T10:00:00+00:00",
            ),
            _event(
                "webhook-newer",
                provider_event_id="evt_newer",
                event_type="checkout.session.completed",
                processed_at="2026-06-22T10:00:00+00:00",
            ),
            _event(
                "webhook-other-tenant",
                provider_event_id="evt_other",
                event_type="checkout.session.completed",
                tenant_id="other-tenant",
                processed_at="2026-06-23T10:00:00+00:00",
            ),
        ]

    def table(self, name: str) -> _Query:
        assert name == "webhook_events"
        return _Query(self.rows)


def _event(
    event_id: str,
    *,
    provider_event_id: str,
    event_type: str,
    processed_at: str,
    tenant_id: str = TENANT_ID,
) -> dict[str, Any]:
    return {
        "id": event_id,
        "provider": "stripe",
        "provider_event_id": provider_event_id,
        "event_type": event_type,
        "tenant_id": tenant_id,
        "processed_at": processed_at,
        "created_at": processed_at,
    }


def test_list_events_returns_tenant_events_newest_first() -> None:
    result = WebhookEventsService(_Db(), TENANT_ID).list_events()  # type: ignore[arg-type]

    assert result.total == 2
    assert [event.id for event in result.items] == ["webhook-newer", "webhook-older"]
    assert result.items[0].provider_event_id == "evt_newer"


def test_list_events_filters_by_provider_event_id_and_type() -> None:
    result = WebhookEventsService(_Db(), TENANT_ID).list_events(  # type: ignore[arg-type]
        provider_event_id="evt_newer",
        event_type="checkout.session.completed",
    )

    assert result.total == 1
    assert result.items[0].id == "webhook-newer"
    assert result.items[0].tenant_id == TENANT_ID
