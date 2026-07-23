"""#379 AC 3 — the trial-balance invariant is not overridable at period close."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.close_override_service import (
    ALLOWED_CLOSE_OVERRIDE_CODES,
    NON_OVERRIDABLE_CLOSE_BLOCKERS,
    CloseOverrideService,
)

pytestmark = pytest.mark.unit


def test_trial_balance_is_non_overridable_and_not_allowed() -> None:
    assert "trial_balance" in NON_OVERRIDABLE_CLOSE_BLOCKERS
    assert "trial_balance" not in ALLOWED_CLOSE_OVERRIDE_CODES


def test_create_override_rejects_trial_balance_code() -> None:
    # Validation happens before any DB access, so a placeholder db is fine.
    svc = CloseOverrideService(db=None, tenant_id="t1")  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as exc:
        svc.create_override(
            period="2026-06",
            blocker_code="trial_balance",
            reason="please just let me close it",
            created_by="u1",
            created_by_role="admin",
        )
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "invalid_close_override_code"


def test_soft_blockers_remain_overridable() -> None:
    # Sanity: the legitimately-overridable codes are still allowed.
    assert {"subledger_reconciliation", "close_reviews", "close_tasks", "unposted_journals"} <= (
        ALLOWED_CLOSE_OVERRIDE_CODES
    )
