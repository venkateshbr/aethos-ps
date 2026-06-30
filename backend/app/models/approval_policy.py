"""Schemas for tenant approval policy controls."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ApprovalRole = Literal["approver", "manager", "admin", "owner"]
ApprovalPolicySource = Literal["system_default", "tenant_default"]

_ROLE_RANK = {"approver": 3, "manager": 4, "admin": 5, "owner": 6}


class ApprovalPolicyConfig(BaseModel):
    """Runtime tenant approval policy used by HITL evaluation."""

    tenant_id: str | None = None
    policy_source: ApprovalPolicySource = "system_default"
    money_out_default_role: ApprovalRole = "admin"
    money_out_owner_threshold: Decimal = Field(default=Decimal("50000"), ge=Decimal("0"))
    money_out_owner_role: ApprovalRole = "owner"
    accounting_role: ApprovalRole = "admin"
    manual_journal_approval_threshold: Decimal = Field(
        default=Decimal("10000"),
        ge=Decimal("0"),
    )
    money_in_role: ApprovalRole = "manager"
    draft_role: ApprovalRole = "manager"
    external_send_role: ApprovalRole = "manager"
    high_risk_role: ApprovalRole = "admin"
    created_at: str | None = None
    updated_at: str | None = None

    @model_validator(mode="after")
    def _validate_safe_floors(self) -> ApprovalPolicyConfig:
        _require_at_least(self.money_out_default_role, "admin", "money_out_default_role")
        _require_at_least(self.money_out_owner_role, "owner", "money_out_owner_role")
        _require_at_least(self.accounting_role, "admin", "accounting_role")
        _require_at_least(self.high_risk_role, "admin", "high_risk_role")
        _require_at_least(self.money_in_role, "approver", "money_in_role")
        _require_at_least(self.draft_role, "approver", "draft_role")
        _require_at_least(self.external_send_role, "approver", "external_send_role")
        return self


class ApprovalPolicyUpsert(BaseModel):
    """Payload for creating or replacing a tenant approval policy."""

    money_out_default_role: ApprovalRole = "admin"
    money_out_owner_threshold: Decimal = Field(default=Decimal("50000"), ge=Decimal("0"))
    money_out_owner_role: ApprovalRole = "owner"
    accounting_role: ApprovalRole = "admin"
    manual_journal_approval_threshold: Decimal = Field(
        default=Decimal("10000"),
        ge=Decimal("0"),
    )
    money_in_role: ApprovalRole = "manager"
    draft_role: ApprovalRole = "manager"
    external_send_role: ApprovalRole = "manager"
    high_risk_role: ApprovalRole = "admin"

    @model_validator(mode="after")
    def _validate_safe_floors(self) -> ApprovalPolicyUpsert:
        ApprovalPolicyConfig(**self.model_dump())
        return self


class ApprovalPolicyResponse(ApprovalPolicyConfig):
    """Effective tenant approval policy returned by the API."""


def _require_at_least(actual: ApprovalRole, minimum: ApprovalRole, field: str) -> None:
    if _ROLE_RANK[actual] < _ROLE_RANK[minimum]:
        raise ValueError(f"{field} cannot be lower than {minimum}")
