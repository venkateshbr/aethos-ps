-- =============================================================================
-- Migration 0111: Out-of-order guard for Stripe subscription webhooks (#371).
-- Stores the unix timestamp (event.created) of the last applied subscription
-- event so a late/duplicate-ordered event cannot clobber newer billing state.
-- =============================================================================

BEGIN;

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS stripe_subscription_event_at BIGINT;

COMMENT ON COLUMN tenants.stripe_subscription_event_at IS
    'Unix timestamp (Stripe event.created) of the last applied subscription '
    'event; guards against out-of-order webhook delivery. (#371 AC 4)';

COMMIT;
