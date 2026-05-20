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
    # Anthropic
    # ------------------------------------------------------------------
    anthropic_api_key: str = ""

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
