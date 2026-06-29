"""Models for tenant AI runtime and inference settings."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

AtlasRuntimeSetting = Literal["aethos_basic", "hermes_agent"]
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


class AiSettingsResponse(AiSettingsUpsert):
    tenant_id: str | None
    policy_source: Literal["system_default", "tenant_default"]
    model_chain: list[str]
    allowed_models: list[AiModelOption]
    created_at: str | None = None
    updated_at: str | None = None
