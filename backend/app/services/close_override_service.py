"""Durable override records for month-end close blockers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status

from app.services.postgrest_errors import is_missing_table_error
from supabase import Client

_TABLE = "accounting_close_overrides"
_MIN_REASON_LENGTH = 10

ALLOWED_CLOSE_OVERRIDE_CODES = frozenset(
    {
        "subledger_reconciliation",
        "trial_balance",
        "close_reviews",
        "close_tasks",
        "unposted_journals",
    }
)


@dataclass(frozen=True)
class CloseOverride:
    id: str
    period: str
    blocker_code: str
    reason: str
    created_by: str
    created_by_role: str
    created_at: str
    blocker_ref: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "period": self.period,
            "blocker_code": self.blocker_code,
            "reason": self.reason,
            "created_by": self.created_by,
            "created_by_role": self.created_by_role,
            "created_at": self.created_at,
            "blocker_ref": self.blocker_ref,
        }


class CloseOverrideService:
    """Read and write audit-visible close blocker override records."""

    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def list_overrides(self, period: str) -> list[CloseOverride]:
        try:
            rows = (
                self.db.table(_TABLE)
                .select("*")
                .eq("tenant_id", self.tenant_id)
                .eq("period", period)
                .is_("deleted_at", "null")
                .order("created_at", desc=True)
                .execute()
                .data
                or []
            )
        except Exception as exc:
            if is_missing_table_error(exc, _TABLE):
                return []
            raise
        return [_override_from_row(row) for row in rows]

    def override_codes(self, period: str) -> set[str]:
        return {override.blocker_code for override in self.list_overrides(period)}

    def create_override(
        self,
        *,
        period: str,
        blocker_code: str,
        reason: str,
        created_by: str,
        created_by_role: str,
        blocker_ref: dict[str, Any] | None = None,
    ) -> CloseOverride:
        blocker_code = blocker_code.strip()
        reason = reason.strip()
        if blocker_code not in ALLOWED_CLOSE_OVERRIDE_CODES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "invalid_close_override_code",
                    "allowed_codes": sorted(ALLOWED_CLOSE_OVERRIDE_CODES),
                },
            )
        if len(reason) < _MIN_REASON_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "close_override_reason_required",
                    "message": "Close override reason must be at least 10 characters.",
                },
            )
        row = (
            self.db.table(_TABLE)
            .insert(
                {
                    "tenant_id": self.tenant_id,
                    "period": period,
                    "blocker_code": blocker_code,
                    "blocker_ref": blocker_ref or {},
                    "reason": reason,
                    "created_by": created_by,
                    "created_by_role": created_by_role,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            )
            .execute()
            .data[0]
        )
        return _override_from_row(row)


def _override_from_row(row: dict[str, Any]) -> CloseOverride:
    blocker_ref = row.get("blocker_ref")
    if not isinstance(blocker_ref, dict):
        blocker_ref = {}
    return CloseOverride(
        id=str(row["id"]),
        period=str(row["period"]),
        blocker_code=str(row["blocker_code"]),
        reason=str(row["reason"]),
        created_by=str(row["created_by"]),
        created_by_role=str(row.get("created_by_role") or "unknown"),
        created_at=str(row["created_at"]),
        blocker_ref=blocker_ref,
    )
