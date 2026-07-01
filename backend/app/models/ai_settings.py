"""Models for tenant AI runtime and inference settings."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

AtlasRuntimeSetting = Literal["aethos_basic", "hermes_agent"]
AtlasResponseStage = Literal["semantic_intent", "atlas_runtime"]
AiProvider = Literal["openrouter"]
AiModelId = Literal[
    "google/gemma-4-31b-it:free",
    "openrouter/free",
    "anthropic/claude-haiku-4.5",
]


class AiModelOption(BaseModel):
    id: AiModelId
    label: str
    cost_class: Literal["free", "router", "paid"]
    description: str


class AiSettingsUpsert(BaseModel):
    atlas_runtime: AtlasRuntimeSetting = "hermes_agent"
    provider: AiProvider = "openrouter"
    primary_model: AiModelId = "google/gemma-4-31b-it:free"
    use_free_router: bool = True
    fallback_model: AiModelId = "anthropic/claude-haiku-4.5"
    semantic_router_enabled: bool = True
    semantic_router_min_confidence: float = Field(default=0.72, ge=0.5, le=0.98)
    atlas_response_order: list[AtlasResponseStage] = Field(
        default_factory=lambda: ["semantic_intent", "atlas_runtime"],
        min_length=1,
        max_length=2,
    )

    @field_validator("atlas_response_order")
    @classmethod
    def validate_response_order(
        cls,
        value: list[AtlasResponseStage],
    ) -> list[AtlasResponseStage]:
        deduped: list[AtlasResponseStage] = []
        for stage in value:
            if stage not in deduped:
                deduped.append(stage)
        if "atlas_runtime" not in deduped:
            deduped.append("atlas_runtime")
        return deduped


class AiSettingsResponse(AiSettingsUpsert):
    tenant_id: str | None
    policy_source: Literal["system_default", "tenant_default"]
    model_chain: list[str]
    allowed_models: list[AiModelOption]
    created_at: str | None = None
    updated_at: str | None = None
