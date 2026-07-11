"""Application settings loaded from environment / .env file.

All configuration is read at import time via pydantic-settings.
Never import this module before process startup (keep tests fast with patch.dict).
"""

from __future__ import annotations

import json
import re
from typing import Annotated

from pydantic import Field, field_validator, model_validator
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
    # Optional separate credential for the built-in Atlas fallback runtime. When
    # empty, the fallback uses OPENROUTER_API_KEY.
    atlas_basic_openrouter_api_key: str = ""
    atlas_basic_openrouter_base_url: str = ""
    # Ordered model fallback chain. OpenRouter tries the first; if it errors or
    # rate-limits, it transparently falls back to the next. Keep OpenRouter's
    # free router after the preferred free model, then a paid Haiku at the tail
    # so the product still works when the free tier is exhausted.
    # NoDecode → bypass pydantic-settings' built-in JSON decoder for complex types,
    # so the field_validator below sees the raw env string and can accept either
    # JSON list ("[a,b,c]") or comma-separated ("a,b,c"). See #96.
    agent_models: Annotated[list[str], NoDecode] = [
        "google/gemma-4-31b-it:free",
        "openrouter/free",
        "anthropic/claude-haiku-4.5",
    ]
    # Legacy — kept so older test configs don't fail to load. Unused.
    anthropic_api_key: str = ""

    # ------------------------------------------------------------------
    # Atlas AI runtime
    # ------------------------------------------------------------------
    # aethos_basic keeps the current built-in Atlas/Copilot agent path.
    # hermes_agent is the future advanced runtime powered by a private Hermes
    # service and Aethos tool broker.
    atlas_ai_runtime: str = "aethos_basic"
    atlas_hermes_api_base_url: str = "http://hermes:8642"
    atlas_hermes_api_server_key: str = ""
    atlas_hermes_timeout_seconds: float = 90.0
    atlas_hide_tool_events: bool = True
    atlas_hermes_fallback_to_basic: bool = False
    aethos_hermes_tool_token: str = ""
    atlas_context_signing_secret: str = ""

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

    @field_validator("atlas_ai_runtime", mode="before")
    @classmethod
    def _validate_atlas_ai_runtime(cls, v: object) -> str:
        value = str(v or "").strip().lower()
        if value not in {"aethos_basic", "hermes_agent"}:
            raise ValueError(
                "ATLAS_AI_RUNTIME must be 'aethos_basic' or 'hermes_agent'"
            )
        return value

    # ------------------------------------------------------------------
    # Langfuse (optional — disabled when empty)
    # ------------------------------------------------------------------
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"
    langfuse_tracing_enabled: bool = True
    langfuse_sample_rate: float = 1.0

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
    # The queue connector owns a psycopg connection pool in every process.
    # Keep the local minimum small; production services override the maximum
    # independently to preserve Supabase session-pool headroom.
    queue_db_pool_min_size: int = Field(default=1, ge=1)
    queue_db_pool_max_size: int = Field(default=4, ge=1)
    queue_db_application_name: str = "aethos-ps-local"
    # When true, /health/ready treats the Procrastinate queue as a required
    # dependency. Keep false for the pilot sync-mode default; set true in
    # deployments where scheduled workers are part of the serving contract.
    queue_required: bool = False

    @field_validator("queue_db_application_name", mode="before")
    @classmethod
    def _validate_queue_db_application_name(cls, value: object) -> str:
        application_name = str(value or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,62}", application_name):
            raise ValueError(
                "QUEUE_DB_APPLICATION_NAME must be 1-63 safe diagnostic characters"
            )
        return application_name

    @model_validator(mode="after")
    def _validate_queue_db_pool_bounds(self) -> Settings:
        if self.queue_db_pool_max_size < self.queue_db_pool_min_size:
            raise ValueError(
                "QUEUE_DB_POOL_MAX_SIZE must be greater than or equal to "
                "QUEUE_DB_POOL_MIN_SIZE"
            )
        return self

    # Legacy — kept so older test configs don't fail to load. Unused since the
    # ARQ → Procrastinate migration moved the queue into Supabase Postgres.
    upstash_redis_url: str = ""

    # ------------------------------------------------------------------
    # Document-extraction dispatch mode
    # ------------------------------------------------------------------
    # `sync`  → extraction runs INLINE in the upload request (blocks 5-30s
    #           while the LLM extracts; user gets immediate feedback). No
    #           Procrastinate worker required. Pilot default.
    # `async` → extraction is deferred onto the Procrastinate queue and the
    #           upload returns immediately. Requires DATABASE_URL set + a
    #           running worker (`python -m procrastinate ... worker`).
    # Defaults to `sync` so a fresh checkout works without queue setup;
    # flip to `async` once the worker is operational.
    extraction_mode: str = "sync"

    # ------------------------------------------------------------------
    # CORS / runtime
    # ------------------------------------------------------------------
    # NoDecode → same reason as agent_models: tolerate shell-mangled list env vars.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:4201"]
    debug: bool = False
    environment: str = "development"

    # ------------------------------------------------------------------
    # App-level rate limiting
    # ------------------------------------------------------------------
    # First slice is intentionally in-process and protects only high-risk
    # public/auth endpoints. Keep thresholds high enough for browser E2E setup.
    rate_limit_enabled: bool = True
    # "memory" is local-process only. "supabase" uses the Postgres-backed
    # `check_rate_limit` RPC from migration 0089 so limits apply across app
    # instances. The distributed backend falls back to memory by default if the
    # RPC is unavailable.
    rate_limit_backend: str = "memory"
    rate_limit_distributed_fallback_to_memory: bool = True
    rate_limit_window_seconds: int = 60
    rate_limit_signup_max_requests: int = 60
    rate_limit_public_invoice_max_requests: int = 300

    # ------------------------------------------------------------------
    # Operator alert routing
    # ------------------------------------------------------------------
    # Empty webhook means "route to runbook queue" in health output. We do not
    # send outbound alerts from request handlers; external routing can poll the
    # safe health API or consume the same thresholds.
    ops_alert_channel: str = "runbook"
    ops_alert_webhook_url: str = ""
    ops_alert_rate_limit_threshold: int = 10
    ops_alert_background_failure_threshold: int = 3
    ops_alert_agent_failure_threshold: int = 1


# Module-level singleton — import this everywhere.
settings = Settings()
