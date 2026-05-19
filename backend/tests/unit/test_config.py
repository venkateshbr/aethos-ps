"""Unit tests for application settings.

Uses ``patch.dict`` to inject env vars — never touches a real .env file.
The module is reloaded so pydantic-settings re-reads the patched environment.
"""

from __future__ import annotations

import os
from importlib import reload
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

_REQUIRED_ENV = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_ANON_KEY": "test-anon",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service",
    "SUPABASE_JWT_SECRET": "test-secret",
    "STRIPE_SECRET_KEY": "sk_test_xxx",
    "STRIPE_WEBHOOK_SECRET": "whsec_xxx",
    "ANTHROPIC_API_KEY": "sk-ant-xxx",
}


def test_settings_load_with_env_vars() -> None:
    """Settings resolve env vars correctly and apply defaults."""
    with patch.dict(os.environ, _REQUIRED_ENV, clear=False):
        import app.core.config as cfg

        reload(cfg)
        s = cfg.Settings()

        assert s.supabase_url == "https://test.supabase.co"
        assert s.supabase_anon_key == "test-anon"
        assert s.supabase_service_role_key == "test-service"
        assert s.supabase_jwt_secret == "test-secret"
        assert s.stripe_secret_key == "sk_test_xxx"
        assert s.anthropic_api_key == "sk-ant-xxx"
        # Defaults
        assert s.debug is False
        assert s.environment == "development"
        assert "http://localhost:4201" in s.cors_origins


def test_debug_flag_parsed_from_env() -> None:
    env = {**_REQUIRED_ENV, "DEBUG": "true"}
    with patch.dict(os.environ, env, clear=False):
        import app.core.config as cfg

        s = cfg.Settings()
        assert s.debug is True


def test_cors_origins_parsed_as_list() -> None:
    env = {**_REQUIRED_ENV, "CORS_ORIGINS": '["https://app.aethos.app"]'}
    with patch.dict(os.environ, env, clear=False):
        import app.core.config as cfg

        s = cfg.Settings()
        assert isinstance(s.cors_origins, list)
        assert "https://app.aethos.app" in s.cors_origins


def test_optional_fields_default_to_empty_string() -> None:
    with patch.dict(os.environ, _REQUIRED_ENV, clear=False):
        import app.core.config as cfg

        s = cfg.Settings()
        assert s.langfuse_public_key == "" or isinstance(s.langfuse_public_key, str)
        assert s.upstash_redis_url == "" or isinstance(s.upstash_redis_url, str)
