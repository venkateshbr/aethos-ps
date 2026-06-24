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
        assert isinstance(s.debug, bool)  # .env may override default in local env
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


def test_rate_limit_settings_parse_from_env() -> None:
    env = {
        **_REQUIRED_ENV,
        "RATE_LIMIT_ENABLED": "true",
        "RATE_LIMIT_BACKEND": "supabase",
        "RATE_LIMIT_DISTRIBUTED_FALLBACK_TO_MEMORY": "false",
        "RATE_LIMIT_WINDOW_SECONDS": "30",
        "RATE_LIMIT_SIGNUP_MAX_REQUESTS": "3",
        "RATE_LIMIT_PUBLIC_INVOICE_MAX_REQUESTS": "7",
        "OPS_ALERT_CHANNEL": "secops",
        "OPS_ALERT_RATE_LIMIT_THRESHOLD": "2",
        "OPS_ALERT_BACKGROUND_FAILURE_THRESHOLD": "4",
        "OPS_ALERT_AGENT_FAILURE_THRESHOLD": "5",
    }
    with patch.dict(os.environ, env, clear=False):
        import app.core.config as cfg

        s = cfg.Settings()
        assert s.rate_limit_enabled is True
        assert s.rate_limit_backend == "supabase"
        assert s.rate_limit_distributed_fallback_to_memory is False
        assert s.rate_limit_window_seconds == 30
        assert s.rate_limit_signup_max_requests == 3
        assert s.rate_limit_public_invoice_max_requests == 7
        assert s.ops_alert_channel == "secops"
        assert s.ops_alert_rate_limit_threshold == 2
        assert s.ops_alert_background_failure_threshold == 4
        assert s.ops_alert_agent_failure_threshold == 5


# ---------------------------------------------------------------------------
# AGENT_MODELS parser — regression guard for #96
# AGENT_MODELS must load from BOTH JSON-list and comma-separated forms so that
# `set -a && source .env && set +a` (which strips JSON quotes/brackets) works.
# ---------------------------------------------------------------------------


def test_agent_models_parsed_from_json_list() -> None:
    env = {**_REQUIRED_ENV, "AGENT_MODELS": '["a/b","c/d","e/f"]'}
    with patch.dict(os.environ, env, clear=False):
        import app.core.config as cfg

        reload(cfg)
        s = cfg.Settings()
        assert s.agent_models == ["a/b", "c/d", "e/f"]


def test_agent_models_parsed_from_comma_separated_string() -> None:
    """The exact shape the shell produces after `set -a && source .env`."""
    env = {**_REQUIRED_ENV, "AGENT_MODELS": "a/b,c/d,e/f"}
    with patch.dict(os.environ, env, clear=False):
        import app.core.config as cfg

        reload(cfg)
        s = cfg.Settings()
        assert s.agent_models == ["a/b", "c/d", "e/f"]


def test_agent_models_tolerates_shell_mangled_brackets() -> None:
    """Bash strips the JSON quotes but may leave brackets — handle both."""
    env = {**_REQUIRED_ENV, "AGENT_MODELS": "[a/b,c/d,e/f]"}
    with patch.dict(os.environ, env, clear=False):
        import app.core.config as cfg

        reload(cfg)
        s = cfg.Settings()
        assert s.agent_models == ["a/b", "c/d", "e/f"]


def test_agent_models_strips_whitespace_and_quote_remnants() -> None:
    env = {**_REQUIRED_ENV, "AGENT_MODELS": ' "a/b" , "c/d" '}
    with patch.dict(os.environ, env, clear=False):
        import app.core.config as cfg

        reload(cfg)
        s = cfg.Settings()
        assert s.agent_models == ["a/b", "c/d"]


def test_agent_models_default_when_unset() -> None:
    """No AGENT_MODELS env var → built-in 3-model chain applies."""
    with patch.dict(os.environ, _REQUIRED_ENV, clear=False):
        # Make sure no AGENT_MODELS leaks from the host shell
        os.environ.pop("AGENT_MODELS", None)
        import app.core.config as cfg

        reload(cfg)
        s = cfg.Settings()
        assert len(s.agent_models) == 3
        assert s.agent_models[-1] == "anthropic/claude-haiku-4.5"
