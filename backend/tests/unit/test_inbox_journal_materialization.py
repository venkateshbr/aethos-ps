"""Inbox materialization tests for HITL-approved journal proposals."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services.inbox_service import InboxService

pytestmark = pytest.mark.unit


def _service() -> InboxService:
    svc = InboxService.__new__(InboxService)
    svc._db = MagicMock()
    svc._tenant_id = "tenant-001"
    return svc


@pytest.mark.asyncio
async def test_materialise_draft_journal_posts_manual_journal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    class _FakeManualJournalService:
        def __init__(self, db: object, tenant_id: str, user_id: str) -> None:
            captured["db"] = db
            captured["tenant_id"] = tenant_id
            captured["user_id"] = user_id

        async def post_manual_journal(self, payload: object) -> object:
            captured["payload"] = payload
            return type("PostedJournal", (), {"id": "journal-001"})()

    monkeypatch.setattr(
        "app.services.manual_journal_service.ManualJournalService",
        _FakeManualJournalService,
    )

    result = await _service()._materialise(
        "draft_journal",
        {
            "description": "Month-end WIP accrual",
            "entry_date": "2026-06-30",
            "reference": "close-2026-06",
            "lines": [
                {
                    "direction": "DR",
                    "account_id": "11111111-1111-1111-1111-111111111111",
                    "amount": "2500.00",
                    "currency": "USD",
                    "description": "Unbilled revenue",
                },
                {
                    "direction": "CR",
                    "account_id": "22222222-2222-2222-2222-222222222222",
                    "amount": "2500.00",
                    "currency": "USD",
                    "description": "Revenue accrual",
                },
            ],
        },
        user_id="approver-001",
    )

    assert result == {"entity_type": "journal_entry", "entity_id": "journal-001"}
    assert captured["tenant_id"] == "tenant-001"
    assert captured["user_id"] == "approver-001"
    assert captured["payload"].description == "Month-end WIP accrual"
    assert captured["payload"].lines[0].amount == captured["payload"].lines[1].amount


@pytest.mark.asyncio
async def test_materialise_draft_journal_requires_deciding_user() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await _service()._materialise(
            "draft_journal",
            {"description": "Missing user", "entry_date": "2026-06-30", "lines": []},
        )

    assert exc_info.value.status_code == 422
    assert "user id" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_materialise_draft_journal_validates_payload() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await _service()._materialise(
            "draft_journal",
            {
                "description": "Invalid journal",
                "entry_date": "2026-06-30",
                "lines": [
                    {
                        "direction": "DR",
                        "account_id": "11111111-1111-1111-1111-111111111111",
                        "amount": "2500.00",
                    }
                ],
            },
            user_id="approver-001",
        )

    assert exc_info.value.status_code == 422
