"""Pydantic request/response schemas for auth and signup endpoints."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    """POST /api/v1/auth/signup — tenant onboarding form."""

    email: EmailStr
    password: str = Field(min_length=8, description="Minimum 8 characters")
    tenant_name: str = Field(min_length=2, max_length=100)
    country: str = Field(
        pattern=r"^[A-Z]{2}$",
        description="ISO 3166-1 alpha-2 country code (uppercase)",
    )
    plan_tier: Literal["starter", "growth", "pro"] = "starter"
    billing_interval: Literal["monthly", "annual"] = "monthly"


class SignupResponse(BaseModel):
    """Response returned after successful signup."""

    tenant_id: str
    stripe_setup_intent_client_secret: str
    message: str = "Signup successful. Complete card setup to start your trial."


class StartTrialRequest(BaseModel):
    """POST /api/v1/billing/start-trial — called after frontend confirms Setup Intent."""

    setup_intent_id: str = Field(min_length=1)
    price_id: str = Field(min_length=1)


class StartTrialResponse(BaseModel):
    """Response after trial subscription is created."""

    subscription_id: str
    status: str
    trial_ends_at: int | None  # Unix timestamp


class BillingPortalRequest(BaseModel):
    """POST /api/v1/billing/portal — initiate a Stripe Customer Portal session."""

    return_url: str = Field(
        default="http://localhost:4201/settings/billing",
        description="URL to redirect back to after the portal session.",
    )

    @field_validator("return_url")
    @classmethod
    def return_url_must_be_same_origin(cls, v: str) -> str:
        """Reject open-redirect: return_url must share origin with frontend_base_url.

        Prevents an attacker from crafting a portal URL that redirects to phishing.
        """
        from app.core.config import settings  # import here to keep model import-safe

        allowed = urlparse(settings.frontend_base_url)
        supplied = urlparse(v)

        if supplied.scheme != allowed.scheme or supplied.netloc != allowed.netloc:
            raise ValueError(
                f"return_url must be on the same origin as the frontend "
                f"({allowed.scheme}://{allowed.netloc})"
            )
        return v


class BillingPortalResponse(BaseModel):
    """URL to redirect the user to the Stripe Customer Portal."""

    url: str


class PriceEntry(BaseModel):
    """A single plan's price IDs for one currency."""

    tier: str
    monthly_id: str | None
    annual_id: str | None


class PriceCatalogueResponse(BaseModel):
    """GET /api/v1/billing/prices — plan picker payload for the frontend."""

    currency: str
    plans: list[PriceEntry]
