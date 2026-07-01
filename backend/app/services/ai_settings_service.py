"""Tenant AI settings persistence and effective model-chain resolution."""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.config import settings
from app.models.ai_settings import AiModelOption, AiSettingsResponse, AiSettingsUpsert
from supabase import Client

_TABLE = "tenant_ai_settings"

DEFAULT_PRIMARY_MODEL = "google/gemma-4-31b-it:free"
FREE_ROUTER_MODEL = "openrouter/free"
DEFAULT_FALLBACK_MODEL = "anthropic/claude-haiku-4.5"
DEFAULT_MODEL_CHAIN = [DEFAULT_PRIMARY_MODEL, FREE_ROUTER_MODEL, DEFAULT_FALLBACK_MODEL]
DEFAULT_ATLAS_RESPONSE_ORDER = ["semantic_intent", "atlas_runtime"]

ALLOWED_MODEL_OPTIONS = [
    AiModelOption(
        id="google/gemma-4-31b-it:free",
        label="Gemma 4 31B IT",
        cost_class="free",
        description="Preferred free primary model for Aethos inference.",
    ),
    AiModelOption(
        id="openrouter/free",
        label="OpenRouter Free Router",
        cost_class="router",
        description="Routes compatible requests across OpenRouter free models.",
    ),
    AiModelOption(
        id="anthropic/claude-haiku-4.5",
        label="Claude Haiku 4.5",
        cost_class="paid",
        description="Stable paid fallback when free models are unavailable.",
    ),
]


class AiSettingsService:
    """Tenant-scoped AI runtime and provider settings."""

    def __init__(self, db: Client, tenant_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id

    async def get_effective_settings(self) -> AiSettingsResponse:
        row = await self._find_settings()
        if row is None:
            return default_ai_settings_response(tenant_id=self._tenant_id)
        return _row_to_response(row)

    async def get_effective_model_chain(self) -> list[str]:
        response = await self.get_effective_settings()
        return response.model_chain

    async def get_effective_runtime(self) -> str:
        response = await self.get_effective_settings()
        return response.atlas_runtime

    async def upsert_settings(self, payload: AiSettingsUpsert) -> AiSettingsResponse:
        data = payload.model_dump(mode="json")
        data["tenant_id"] = self._tenant_id
        result = await asyncio.to_thread(
            lambda: self._db.table(_TABLE).upsert(data, on_conflict="tenant_id").execute()
        )
        rows = result.data or []
        if rows:
            return _row_to_response(rows[0])
        refreshed = await self._find_settings()
        if refreshed is None:
            return AiSettingsResponse(
                tenant_id=self._tenant_id,
                policy_source="tenant_default",
                model_chain=build_model_chain(payload),
                allowed_models=ALLOWED_MODEL_OPTIONS,
                **payload.model_dump(),
            )
        return _row_to_response(refreshed)

    async def _find_settings(self) -> dict[str, Any] | None:
        result = await asyncio.to_thread(
            lambda: (
                self._db.table(_TABLE)
                .select("*")
                .eq("tenant_id", self._tenant_id)
                .limit(1)
                .execute()
            )
        )
        rows = result.data or []
        return rows[0] if rows else None


def build_model_chain(payload: AiSettingsUpsert) -> list[str]:
    """Return a de-duplicated OpenRouter model chain in execution order."""
    chain = [payload.primary_model]
    if payload.use_free_router:
        chain.append(FREE_ROUTER_MODEL)
    chain.append(payload.fallback_model)
    deduped: list[str] = []
    for model in chain:
        if model not in deduped:
            deduped.append(model)
    return deduped


def default_ai_settings_response(*, tenant_id: str | None = None) -> AiSettingsResponse:
    """System default shown before a tenant override exists.

    The model chain is pinned to the current product default. Runtime defaults to
    the deployment setting so local/dev environments can stay on Aethos Basic
    while Hostinger can run Hermes.
    """
    runtime = settings.atlas_ai_runtime
    return AiSettingsResponse(
        tenant_id=tenant_id,
        policy_source="system_default",
        atlas_runtime=runtime,  # type: ignore[arg-type]
        provider="openrouter",
        primary_model=DEFAULT_PRIMARY_MODEL,
        use_free_router=True,
        fallback_model=DEFAULT_FALLBACK_MODEL,
        semantic_router_enabled=True,
        semantic_router_min_confidence=0.72,
        atlas_response_order=list(DEFAULT_ATLAS_RESPONSE_ORDER),
        model_chain=list(DEFAULT_MODEL_CHAIN),
        allowed_models=ALLOWED_MODEL_OPTIONS,
        created_at=None,
        updated_at=None,
    )


def _row_to_response(row: dict[str, Any]) -> AiSettingsResponse:
    payload = AiSettingsUpsert(
        atlas_runtime=row.get("atlas_runtime") or settings.atlas_ai_runtime,
        provider=row.get("provider") or "openrouter",
        primary_model=row.get("primary_model") or DEFAULT_PRIMARY_MODEL,
        use_free_router=bool(row.get("use_free_router", True)),
        fallback_model=row.get("fallback_model") or DEFAULT_FALLBACK_MODEL,
        semantic_router_enabled=bool(row.get("semantic_router_enabled", True)),
        semantic_router_min_confidence=float(row.get("semantic_router_min_confidence") or 0.72),
        atlas_response_order=_response_order_from_row(row.get("atlas_response_order")),
    )
    return AiSettingsResponse(
        tenant_id=str(row.get("tenant_id") or ""),
        policy_source="tenant_default",
        model_chain=build_model_chain(payload),
        allowed_models=ALLOWED_MODEL_OPTIONS,
        created_at=str(row["created_at"]) if row.get("created_at") else None,
        updated_at=str(row["updated_at"]) if row.get("updated_at") else None,
        **payload.model_dump(),
    )


def _response_order_from_row(value: object) -> list[str]:
    if isinstance(value, list):
        candidate = [str(item) for item in value]
    elif isinstance(value, str) and value.strip():
        trimmed = value.strip("{}")
        candidate = [item.strip().strip('"') for item in trimmed.split(",") if item.strip()]
    else:
        candidate = list(DEFAULT_ATLAS_RESPONSE_ORDER)
    allowed = {"semantic_intent", "atlas_runtime"}
    deduped: list[str] = []
    for stage in candidate:
        if stage in allowed and stage not in deduped:
            deduped.append(stage)
    if "atlas_runtime" not in deduped:
        deduped.append("atlas_runtime")
    return deduped
