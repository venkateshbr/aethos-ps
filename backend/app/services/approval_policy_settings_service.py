"""Tenant approval policy persistence and runtime mapping."""

from __future__ import annotations

import asyncio

from app.models.approval_policy import ApprovalPolicyResponse, ApprovalPolicyUpsert
from app.services.approval_policy import (
    ApprovalPolicySettings,
    approval_policy_settings_from_mapping,
    default_approval_policy_settings,
)
from supabase import Client

_TABLE = "tenant_approval_policies"


class ApprovalPolicySettingsService:
    """Tenant-scoped approval policy access."""

    def __init__(self, db: Client, tenant_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id

    async def get_effective_policy(self) -> ApprovalPolicyResponse:
        row = await self._find_policy()
        if row is None:
            return _settings_to_response(
                default_approval_policy_settings(),
                tenant_id=self._tenant_id,
                created_at=None,
                updated_at=None,
            )
        return _row_to_response(row)

    async def get_runtime_settings(self) -> ApprovalPolicySettings:
        row = await self._find_policy()
        if row is None:
            return default_approval_policy_settings()
        return approval_policy_settings_from_mapping(
            row,
            policy_source="tenant_default",
        )

    async def upsert_policy(
        self,
        payload: ApprovalPolicyUpsert,
    ) -> ApprovalPolicyResponse:
        data = payload.model_dump(mode="json")
        data["tenant_id"] = self._tenant_id
        result = await asyncio.to_thread(
            lambda: self._db.table(_TABLE)
            .upsert(data, on_conflict="tenant_id")
            .execute()
        )
        rows = result.data or []
        if rows:
            return _row_to_response(rows[0])
        refreshed = await self._find_policy()
        if refreshed is None:
            return ApprovalPolicyResponse(
                tenant_id=self._tenant_id,
                policy_source="tenant_default",
                **payload.model_dump(),
            )
        return _row_to_response(refreshed)

    async def _find_policy(self) -> dict | None:
        result = await asyncio.to_thread(
            lambda: self._db.table(_TABLE)
            .select("*")
            .eq("tenant_id", self._tenant_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None


def _row_to_response(row: dict) -> ApprovalPolicyResponse:
    return ApprovalPolicyResponse(
        tenant_id=str(row.get("tenant_id") or ""),
        policy_source="tenant_default",
        money_out_default_role=row.get("money_out_default_role") or "admin",
        money_out_owner_threshold=row.get("money_out_owner_threshold") or "50000",
        money_out_owner_role=row.get("money_out_owner_role") or "owner",
        accounting_role=row.get("accounting_role") or "admin",
        manual_journal_approval_threshold=(
            row.get("manual_journal_approval_threshold") or "10000"
        ),
        money_in_role=row.get("money_in_role") or "manager",
        draft_role=row.get("draft_role") or "manager",
        external_send_role=row.get("external_send_role") or "manager",
        high_risk_role=row.get("high_risk_role") or "admin",
        created_at=str(row["created_at"]) if row.get("created_at") else None,
        updated_at=str(row["updated_at"]) if row.get("updated_at") else None,
    )


def _settings_to_response(
    settings: ApprovalPolicySettings,
    *,
    tenant_id: str,
    created_at: str | None,
    updated_at: str | None,
) -> ApprovalPolicyResponse:
    return ApprovalPolicyResponse(
        tenant_id=tenant_id,
        policy_source="system_default",
        money_out_default_role=settings.money_out_default_role.value,
        money_out_owner_threshold=settings.money_out_owner_threshold,
        money_out_owner_role=settings.money_out_owner_role.value,
        accounting_role=settings.accounting_role.value,
        manual_journal_approval_threshold=settings.manual_journal_approval_threshold,
        money_in_role=settings.money_in_role.value,
        draft_role=settings.draft_role.value,
        external_send_role=settings.external_send_role.value,
        high_risk_role=settings.high_risk_role.value,
        created_at=created_at,
        updated_at=updated_at,
    )
