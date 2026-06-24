"""Pydantic schemas for collections reminder policies."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

CollectionTone = Literal["gentle", "firm", "final"]
MaxAutoSendTone = Literal["none", "gentle", "firm", "final"]
CollectionsPolicySource = Literal["system_default", "tenant_default", "client_override"]


class CollectionsPolicyConfig(BaseModel):
    """Runtime policy consumed by the collections agent and worker."""

    id: str | None = None
    client_id: str | None = None
    policy_source: CollectionsPolicySource = "system_default"
    is_enabled: bool = True
    gentle_after_days: int = Field(default=1, ge=1, le=365)
    firm_after_days: int = Field(default=8, ge=1, le=365)
    final_after_days: int = Field(default=31, ge=1, le=365)
    cooldown_days: int = Field(default=7, ge=1, le=365)
    max_reminders_per_invoice: int = Field(default=3, ge=1, le=20)
    max_auto_send_tone: MaxAutoSendTone = "final"

    @model_validator(mode="after")
    def _validate_stage_order(self) -> CollectionsPolicyConfig:
        if self.firm_after_days < self.gentle_after_days:
            raise ValueError("firm_after_days must be >= gentle_after_days")
        if self.final_after_days < self.firm_after_days:
            raise ValueError("final_after_days must be >= firm_after_days")
        return self


class CollectionsPolicyUpsert(BaseModel):
    """Payload for creating or replacing a tenant/client collections policy."""

    is_enabled: bool = True
    gentle_after_days: int = Field(default=1, ge=1, le=365)
    firm_after_days: int = Field(default=8, ge=1, le=365)
    final_after_days: int = Field(default=31, ge=1, le=365)
    cooldown_days: int = Field(default=7, ge=1, le=365)
    max_reminders_per_invoice: int = Field(default=3, ge=1, le=20)
    max_auto_send_tone: MaxAutoSendTone = "final"

    @model_validator(mode="after")
    def _validate_stage_order(self) -> CollectionsPolicyUpsert:
        if self.firm_after_days < self.gentle_after_days:
            raise ValueError("firm_after_days must be >= gentle_after_days")
        if self.final_after_days < self.firm_after_days:
            raise ValueError("final_after_days must be >= firm_after_days")
        return self


class CollectionsPolicyResponse(CollectionsPolicyConfig):
    """Policy representation returned by the API."""


class CollectionsPolicyListResponse(BaseModel):
    items: list[CollectionsPolicyResponse]
    total: int
