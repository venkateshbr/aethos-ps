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
from unittest.mock import MagicMock

import pytest

from app.agents.base import AgentDeps
from app.agents.collections_agent import CollectionsDraft, draft_collection_email

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
