"""Domain exceptions for Aethos PS.

These are business-logic exceptions raised by the service layer.
They are mapped to HTTP responses at the router boundary — never propagate
Stripe/Supabase SDK errors directly to the API caller.
"""

from __future__ import annotations


class AethosError(Exception):
    """Base class for all Aethos domain errors."""


class BillingError(AethosError):
    """Raised when a Stripe or billing operation fails.

    The ``code`` field mirrors the Stripe error code when applicable so the
    caller can distinguish card-declined from API-key errors.
    """

    def __init__(self, message: str, code: str = "billing_error") -> None:
        super().__init__(message)
        self.code = code


class TenantNotFoundError(AethosError):
    """Tenant lookup returned no result."""


class DuplicateSignupError(AethosError):
    """A user with this email already exists."""


class WebhookVerificationError(AethosError):
    """Stripe webhook signature did not verify."""
