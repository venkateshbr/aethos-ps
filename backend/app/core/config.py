"""Application settings loaded from environment / .env file.

All configuration is read at import time via pydantic-settings.
Never import this module before process startup (keep tests fast with patch.dict).
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Supabase
    # ------------------------------------------------------------------
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # ------------------------------------------------------------------
    # Stripe
    # ------------------------------------------------------------------
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # ------------------------------------------------------------------
    # Anthropic
    # ------------------------------------------------------------------
    anthropic_api_key: str = ""

    # ------------------------------------------------------------------
    # Langfuse (optional — disabled when empty)
    # ------------------------------------------------------------------
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    # ------------------------------------------------------------------
    # Upstash Redis (optional — disabled when empty)
    # ------------------------------------------------------------------
    upstash_redis_url: str = ""

    # ------------------------------------------------------------------
    # CORS / runtime
    # ------------------------------------------------------------------
    cors_origins: list[str] = ["http://localhost:4201"]
    debug: bool = False
    environment: str = "development"


# Module-level singleton — import this everywhere.
settings = Settings()
