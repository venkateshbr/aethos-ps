from __future__ import annotations

import pytest

from app.models.ai_settings import AiSettingsUpsert
from app.services.ai_settings_service import (
    DEFAULT_MODEL_CHAIN,
    build_model_chain,
    default_ai_settings_response,
)

pytestmark = pytest.mark.unit


def test_default_ai_settings_chain_prefers_gemma_free_router_then_haiku() -> None:
    response = default_ai_settings_response(tenant_id="tenant-1")

    assert response.provider == "openrouter"
    assert response.primary_model == "google/gemma-4-31b-it:free"
    assert response.use_free_router is True
    assert response.fallback_model == "anthropic/claude-haiku-4.5"
    assert response.model_chain == DEFAULT_MODEL_CHAIN
    assert response.model_chain == [
        "google/gemma-4-31b-it:free",
        "openrouter/free",
        "anthropic/claude-haiku-4.5",
    ]


def test_build_model_chain_deduplicates_free_router() -> None:
    payload = AiSettingsUpsert(
        primary_model="openrouter/free",
        use_free_router=True,
        fallback_model="anthropic/claude-haiku-4.5",
    )

    assert build_model_chain(payload) == [
        "openrouter/free",
        "anthropic/claude-haiku-4.5",
    ]


def test_build_model_chain_can_disable_free_router() -> None:
    payload = AiSettingsUpsert(
        primary_model="google/gemma-4-31b-it:free",
        use_free_router=False,
        fallback_model="anthropic/claude-haiku-4.5",
    )

    assert build_model_chain(payload) == [
        "google/gemma-4-31b-it:free",
        "anthropic/claude-haiku-4.5",
    ]
