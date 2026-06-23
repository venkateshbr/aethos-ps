"""Unit tests for the collections_agent drafting function.

All tests are pure-Python with no I/O — the Supabase client is mocked via a
lightweight stub so we never hit the network.

Verified behaviours:
  - Tone tier selection by days_overdue
  - escalation_recommended flag for "final" tone
  - invoice_number appears in the draft subject / body
  - confidence is in [0.0, 1.0]
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.agents.base import AgentDeps
from app.agents.collections_agent import (
    CollectionsDraft,
    collection_tone_for_days,
    draft_collection_email,
    policy_allows_auto_send,
)
from app.models.collections_policy import CollectionsPolicyConfig

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_deps(tenant_id: str = "t1") -> AgentDeps:
    """Return an AgentDeps whose DB client is a MagicMock."""
    db = MagicMock()
    # .table(...).select(...).eq(...).execute() → MagicMock with .data = []
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    return AgentDeps(tenant_id=tenant_id, user_id=None, db=db)


def _make_invoice(days_overdue: int, invoice_number: str = "INV-001") -> dict:
    """Build a minimal invoice dict with due_date set to produce *days_overdue*."""
    due = date.today() - timedelta(days=days_overdue)
    return {
        "id": "inv-uuid-1",
        "invoice_number": invoice_number,
        "total": "1500.00",
        "currency": "USD",
        "due_date": due.isoformat(),
        "client_id": "client-uuid-1",
        "stripe_payment_link_url": "",
    }


# ---------------------------------------------------------------------------
# Tone tiers
# ---------------------------------------------------------------------------


def test_gentle_tone_for_1_to_7_days() -> None:
    """Invoices 1-7 days overdue get the 'gentle' tone."""
    draft = draft_collection_email(_make_invoice(days_overdue=3), _make_deps())
    assert draft.tone == "gentle"
    assert draft.escalation_recommended is False


def test_firm_tone_for_8_to_30_days() -> None:
    """Invoices 8-30 days overdue get the 'firm' tone."""
    draft = draft_collection_email(_make_invoice(days_overdue=15), _make_deps())
    assert draft.tone == "firm"
    assert draft.escalation_recommended is False


def test_final_tone_over_30_days() -> None:
    """Invoices > 30 days overdue get the 'final' tone with escalation flag."""
    draft = draft_collection_email(_make_invoice(days_overdue=45), _make_deps())
    assert draft.tone == "final"
    assert draft.escalation_recommended is True


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------


def test_draft_contains_invoice_number() -> None:
    """The invoice number must appear in both the subject and the body HTML."""
    inv = _make_invoice(days_overdue=5, invoice_number="INV-2024-007")
    draft = draft_collection_email(inv, _make_deps())
    assert "INV-2024-007" in draft.subject
    assert "INV-2024-007" in draft.body_html


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------


def test_confidence_in_range() -> None:
    """Default confidence must be within [0.0, 1.0] and pass Pydantic validation."""
    draft = draft_collection_email(_make_invoice(days_overdue=10), _make_deps())
    assert 0.0 <= draft.confidence <= 1.0


# ---------------------------------------------------------------------------
# Model validation
# ---------------------------------------------------------------------------


def test_collections_draft_rejects_confidence_out_of_range() -> None:
    """CollectionsDraft must reject confidence values outside [0, 1]."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CollectionsDraft(
            invoice_id="x",
            client_name="A",
            client_email="",
            invoice_number="INV-1",
            amount_due=Decimal("100"),
            currency="USD",
            days_overdue=5,
            tone="gentle",
            subject="s",
            body_html="b",
            confidence=1.5,  # invalid
        )


def test_amount_due_is_decimal() -> None:
    """amount_due on the draft must be a Decimal (not float)."""
    draft = draft_collection_email(_make_invoice(days_overdue=3), _make_deps())
    assert isinstance(draft.amount_due, Decimal)


@pytest.mark.asyncio
async def test_inbox_materialises_collections_email(monkeypatch: pytest.MonkeyPatch) -> None:
    """Approving a collections HITL task sends the drafted reminder email."""
    from app.services.inbox_service import InboxService

    sent: list[tuple[str, str, str]] = []

    class _Resend:
        def send_email(self, to: str, subject: str, body_html: str) -> dict:
            sent.append((to, subject, body_html))
            return {"id": "email-1"}

    monkeypatch.setattr("app.services.resend_service.ResendService", lambda: _Resend())

    svc = InboxService.__new__(InboxService)
    result = await svc._materialise_collections_email(
        {
            "invoice_id": "inv-1",
            "client_email": "finance@example.com",
            "subject": "Payment overdue",
            "body_html": "<p>Please pay</p>",
        }
    )

    assert result == {
        "entity_type": "collections_email",
        "entity_id": "inv-1",
        "send_status": "sent",
    }
    assert sent == [("finance@example.com", "Payment overdue", "<p>Please pay</p>")]


@pytest.mark.asyncio
async def test_inbox_materialise_collections_email_raises_on_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provider failures keep the HITL task unresolved by raising 409."""
    from fastapi import HTTPException

    from app.services.inbox_service import InboxService

    class _Resend:
        def send_email(self, _to: str, _subject: str, _body_html: str) -> dict:
            return {"status": "error", "error": "provider down"}

    monkeypatch.setattr("app.services.resend_service.ResendService", lambda: _Resend())

    svc = InboxService.__new__(InboxService)
    with pytest.raises(HTTPException) as exc_info:
        await svc._materialise_collections_email(
            {
                "invoice_id": "inv-1",
                "client_email": "finance@example.com",
                "subject": "Payment overdue",
                "body_html": "<p>Please pay</p>",
            }
        )

    assert exc_info.value.status_code == 409


class _Result:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _Query:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self._filters: list[tuple[str, str, Any]] = []
        self._limit: int | None = None

    def select(self, _columns: str) -> _Query:
        return self

    def eq(self, field: str, value: Any) -> _Query:
        self._filters.append(("eq", field, value))
        return self

    def in_(self, field: str, values: list[Any]) -> _Query:
        self._filters.append(("in", field, values))
        return self

    def gte(self, field: str, value: Any) -> _Query:
        self._filters.append(("gte", field, value))
        return self

    def is_(self, field: str, value: Any) -> _Query:
        self._filters.append(("is", field, value))
        return self

    def limit(self, count: int) -> _Query:
        self._limit = count
        return self

    def execute(self) -> _Result:
        rows = [row for row in self._rows if self._matches(row)]
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Result(rows)

    def _matches(self, row: dict) -> bool:
        for op, field, value in self._filters:
            current = row.get(field)
            if op == "eq" and current != value:
                return False
            if op == "in" and current not in value and str(current) not in {str(v) for v in value}:
                return False
            if op == "gte" and str(current or "") < str(value):
                return False
            if op == "is" and value == "null" and current is not None:
                return False
        return True


class _Db:
    def __init__(self, suggestions: list[dict]) -> None:
        self.suggestions = suggestions

    def table(self, name: str) -> _Query:
        assert name == "agent_suggestions"
        return _Query(self.suggestions)


def test_collections_duplicate_guard_matches_related_entity() -> None:
    """Recent same-invoice same-tone suggestions suppress duplicate reminders."""
    from app.workers.collections import _recent_collections_action_exists

    db = _Db(
        [
            {
                "tenant_id": "tenant-001",
                "agent_name": "collections_agent",
                "action_type": "send_email",
                "status": "pending",
                "created_at": date.today().isoformat(),
                "related_entity_id": "invoice-001",
                "output_snapshot": {"invoice_id": "invoice-001", "tone": "firm"},
            }
        ]
    )

    assert _recent_collections_action_exists(db, "tenant-001", "invoice-001", "firm") is True  # type: ignore[arg-type]
    assert _recent_collections_action_exists(db, "tenant-001", "invoice-001", "final") is False  # type: ignore[arg-type]


def test_collections_duplicate_guard_matches_legacy_output_invoice_id() -> None:
    """Rows written before related_entity_id still suppress by output invoice_id."""
    from app.workers.collections import _recent_collections_action_exists

    db = _Db(
        [
            {
                "tenant_id": "tenant-001",
                "agent_name": "collections_agent",
                "action_type": "send_email",
                "status": "approved",
                "created_at": date.today().isoformat(),
                "related_entity_id": None,
                "output_snapshot": {"invoice_id": "invoice-002", "tone": "gentle"},
            }
        ]
    )

    assert _recent_collections_action_exists(db, "tenant-001", "invoice-002", "gentle") is True  # type: ignore[arg-type]


def test_collections_policy_thresholds_drive_tone() -> None:
    """Tenant policy thresholds replace the fixed 7/30 day buckets."""
    policy = CollectionsPolicyConfig(
        gentle_after_days=3,
        firm_after_days=10,
        final_after_days=20,
    )

    assert collection_tone_for_days(2, policy) is None
    assert collection_tone_for_days(3, policy) == "gentle"
    assert collection_tone_for_days(10, policy) == "firm"
    assert collection_tone_for_days(20, policy) == "final"


def test_disabled_collections_policy_suppresses_tone() -> None:
    policy = CollectionsPolicyConfig(is_enabled=False)

    assert collection_tone_for_days(45, policy) is None


def test_collections_policy_caps_auto_send_by_tone() -> None:
    policy = CollectionsPolicyConfig(max_auto_send_tone="gentle")

    assert policy_allows_auto_send(policy, "gentle") is True
    assert policy_allows_auto_send(policy, "firm") is False
    assert policy_allows_auto_send(CollectionsPolicyConfig(max_auto_send_tone="none"), "gentle") is False


def test_draft_includes_policy_snapshot_fields() -> None:
    policy = CollectionsPolicyConfig(
        id="policy-001",
        policy_source="tenant_default",
        cooldown_days=14,
        max_reminders_per_invoice=2,
    )

    draft = draft_collection_email(
        _make_invoice(days_overdue=16),
        _make_deps(),
        policy=policy,
    )

    assert draft.tone == "firm"
    assert draft.policy_id == "policy-001"
    assert draft.policy_source == "tenant_default"
    assert draft.cooldown_days == 14
    assert draft.max_reminders_per_invoice == 2


class _MultiTableDb:
    def __init__(self, tables: dict[str, list[dict]]) -> None:
        self.tables = tables

    def table(self, name: str) -> _Query:
        return _Query(self.tables.get(name, []))


def test_collections_policy_resolution_prefers_client_override() -> None:
    from app.workers.collections import _resolve_collections_policy

    db = _MultiTableDb(
        {
            "collections_policies": [
                {
                    "id": "tenant-policy",
                    "tenant_id": "tenant-001",
                    "client_id": None,
                    "is_enabled": True,
                    "gentle_after_days": 1,
                    "firm_after_days": 8,
                    "final_after_days": 31,
                    "cooldown_days": 7,
                    "max_reminders_per_invoice": 3,
                    "max_auto_send_tone": "final",
                    "deleted_at": None,
                },
                {
                    "id": "client-policy",
                    "tenant_id": "tenant-001",
                    "client_id": "client-001",
                    "is_enabled": True,
                    "gentle_after_days": 5,
                    "firm_after_days": 15,
                    "final_after_days": 45,
                    "cooldown_days": 10,
                    "max_reminders_per_invoice": 2,
                    "max_auto_send_tone": "gentle",
                    "deleted_at": None,
                },
            ]
        }
    )

    policy = _resolve_collections_policy(db, "tenant-001", "client-001")  # type: ignore[arg-type]

    assert policy.id == "client-policy"
    assert policy.policy_source == "client_override"
    assert policy.gentle_after_days == 5
    assert policy.max_auto_send_tone == "gentle"


def test_collections_action_count_matches_related_entity_and_legacy_payload() -> None:
    from app.workers.collections import _collections_action_count

    db = _MultiTableDb(
        {
            "agent_suggestions": [
                {
                    "tenant_id": "tenant-001",
                    "agent_name": "collections_agent",
                    "action_type": "send_email",
                    "status": "pending",
                    "related_entity_id": "invoice-001",
                    "output_snapshot": {"invoice_id": "invoice-001", "tone": "gentle"},
                },
                {
                    "tenant_id": "tenant-001",
                    "agent_name": "collections_agent",
                    "action_type": "send_email",
                    "status": "approved",
                    "related_entity_id": None,
                    "output_snapshot": {"invoice_id": "invoice-001", "tone": "firm"},
                },
                {
                    "tenant_id": "tenant-001",
                    "agent_name": "collections_agent",
                    "action_type": "send_email",
                    "status": "rejected",
                    "related_entity_id": "invoice-001",
                    "output_snapshot": {"invoice_id": "invoice-001", "tone": "final"},
                },
            ]
        }
    )

    assert _collections_action_count(db, "tenant-001", "invoice-001") == 2  # type: ignore[arg-type]
