"""Unit tests for Inbox API request normalization."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.unit


def test_inbox_task_status_pending_aliases_to_open() -> None:
    from app.api.v1.endpoints.inbox import _normalise_task_status

    assert _normalise_task_status("pending") == "open"
    assert _normalise_task_status("open") == "open"
    assert _normalise_task_status("all") is None


def test_inbox_task_status_unknown_returns_422() -> None:
    from app.api.v1.endpoints.inbox import _normalise_task_status

    with pytest.raises(HTTPException) as exc_info:
        _normalise_task_status("pending_review")

    assert exc_info.value.status_code == 422
