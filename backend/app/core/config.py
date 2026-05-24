"""Application settings loaded from environment / .env file.

All configuration is read at import time via pydantic-settings.
Never import this module before process startup (keep tests fast with patch.dict).
"""

from __future__ import annotations

import json
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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
    # Stripe Connect Standard — client_id from Connect > Settings in Stripe dashboard
    stripe_connect_client_id: str = ""

    # Stripe Price IDs — one per plan x interval x currency.
    # Placeholder values; founder creates real Prices in the Stripe dashboard and
    # sets these in .env (test mode) / secrets manager (production).
    # Naming: STRIPE_PRICE_{TIER}_{INTERVAL}_{CURRENCY}
    stripe_price_starter_monthly_usd: str = "price_starter_monthly_usd"
    stripe_price_starter_monthly_gbp: str = "price_starter_monthly_gbp"
    stripe_price_starter_monthly_sgd: str = "price_starter_monthly_sgd"
    stripe_price_starter_monthly_inr: str = "price_starter_monthly_inr"
    stripe_price_starter_monthly_aud: str = "price_starter_monthly_aud"
    stripe_price_starter_annual_usd: str = "price_starter_annual_usd"
    stripe_price_starter_annual_gbp: str = "price_starter_annual_gbp"
    stripe_price_starter_annual_sgd: str = "price_starter_annual_sgd"
    stripe_price_starter_annual_inr: str = "price_starter_annual_inr"
    stripe_price_starter_annual_aud: str = "price_starter_annual_aud"

    stripe_price_growth_monthly_usd: str = "price_growth_monthly_usd"
    stripe_price_growth_monthly_gbp: str = "price_growth_monthly_gbp"
    stripe_price_growth_monthly_sgd: str = "price_growth_monthly_sgd"
    stripe_price_growth_monthly_inr: str = "price_growth_monthly_inr"
    stripe_price_growth_monthly_aud: str = "price_growth_monthly_aud"
    stripe_price_growth_annual_usd: str = "price_growth_annual_usd"
    stripe_price_growth_annual_gbp: str = "price_growth_annual_gbp"
    stripe_price_growth_annual_sgd: str = "price_growth_annual_sgd"
    stripe_price_growth_annual_inr: str = "price_growth_annual_inr"
    stripe_price_growth_annual_aud: str = "price_growth_annual_aud"

    stripe_price_pro_monthly_usd: str = "price_pro_monthly_usd"
    stripe_price_pro_monthly_gbp: str = "price_pro_monthly_gbp"
    stripe_price_pro_monthly_sgd: str = "price_pro_monthly_sgd"
    stripe_price_pro_monthly_inr: str = "price_pro_monthly_inr"
    stripe_price_pro_monthly_aud: str = "price_pro_monthly_aud"
    stripe_price_pro_annual_usd: str = "price_pro_annual_usd"
    stripe_price_pro_annual_gbp: str = "price_pro_annual_gbp"
    stripe_price_pro_annual_sgd: str = "price_pro_annual_sgd"
    stripe_price_pro_annual_inr: str = "price_pro_annual_inr"
    stripe_price_pro_annual_aud: str = "price_pro_annual_aud"

    # Frontend base URL — used to construct billing portal return URLs.
    frontend_base_url: str = "http://localhost:4201"

    # ------------------------------------------------------------------
    # LLM provider (OpenRouter — OpenAI-compatible API)
    # ------------------------------------------------------------------
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Ordered model fallback chain. OpenRouter tries the first; if it errors or
    # rate-limits, it transparently falls back to the next. Keep a paid Haiku at
    # the tail so the product still works when the free tier is exhausted.
    # NoDecode → bypass pydantic-settings' built-in JSON decoder for complex types,
    # so the field_validator below sees the raw env string and can accept either
    # JSON list ("[a,b,c]") or comma-separated ("a,b,c"). See #96.
    agent_models: Annotated[list[str], NoDecode] = [
        "google/gemma-4-31b-it:free",
        "google/gemma-4-26b-a4b-it:free",
        "anthropic/claude-haiku-4.5",
    ]
    # Legacy — kept so older test configs don't fail to load. Unused.
    anthropic_api_key: str = ""

    @field_validator("agent_models", "cors_origins", mode="before")
    @classmethod
    def _parse_str_list(cls, v: object) -> object:
        """Accept JSON list OR comma-separated string for list[str] env vars.

        Why both: ``pydantic-settings`` defaults to JSON-parsing list-typed env
        vars. That works when pydantic loads ``.env`` directly, but breaks the
        common ``set -a && source .env && set +a`` workflow because the shell
        strips JSON quotes/brackets before pydantic ever sees the value.
        Combined with ``Annotated[..., NoDecode]`` on the field, this validator
        receives the raw env string and tolerates both shapes. (See #96.)
        """
        if v is None or isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("["):
                try:
                    return json.loads(s)
                except json.JSONDecodeError:
                    s = s.strip("[]")
            return [item.strip().strip('"').strip("'") for item in s.split(",") if item.strip()]
        return v

    # ------------------------------------------------------------------
    # Langfuse (optional — disabled when empty)
    # ------------------------------------------------------------------
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    # ------------------------------------------------------------------
    # FX Rates (Open Exchange Rates — free tier works without an app_id)
    # ------------------------------------------------------------------
    openexchangerates_app_id: str = ""

    # ------------------------------------------------------------------
    # Resend (transactional email — disabled when empty)
    # ------------------------------------------------------------------
    resend_api_key: str = ""

    # ------------------------------------------------------------------
    # Task queue (Procrastinate — Postgres-backed; lives in Supabase)
    # ------------------------------------------------------------------
    # Direct Postgres connection string for the Procrastinate queue.
    # Format: postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres
    # Pooler (recommended for serverless workers):
    #   postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
    # Use the SESSION pooler (5432) not transaction pooler (6543) — Procrastinate
    # needs LISTEN/NOTIFY which transaction pooling doesn't support.
    database_url: str = ""

    # Legacy — kept so older test configs don't fail to load. Unused since the
    # ARQ → Procrastinate migration moved the queue into Supabase Postgres.
    upstash_redis_url: str = ""

    # ------------------------------------------------------------------
    # CORS / runtime
    # ------------------------------------------------------------------
    # NoDecode → same reason as agent_models: tolerate shell-mangled list env vars.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:4201"]
    debug: bool = False
    environment: str = "development"


# Module-level singleton — import this everywhere.
settings = Settings()
