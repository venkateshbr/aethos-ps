"""FastAPI dependency for StripeService.

Provides a singleton StripeService per process (settings don't change).
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.services.billing.stripe_service import StripeService


@lru_cache(maxsize=1)
def get_stripe_service() -> StripeService:
    """Return the shared StripeService instance."""
    return StripeService(settings)
