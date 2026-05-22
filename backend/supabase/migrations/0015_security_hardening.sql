-- =============================================================================
-- Migration 0015: Security hardening — Prahari audit 2026-05-23
-- Issue: #72
-- =============================================================================
-- Fixes two gaps found in the pre-launch security audit:
--
-- 1. tenants table was missing RLS.  A service-role client is used for all
--    writes, but the anon / authenticated key was unguarded.  A deny-all
--    RLS policy is correct here because tenants is accessed exclusively via
--    the service-role client in the application layer — authenticated users
--    never query this table directly.
--
-- 2. webhook_events table is referenced by the application but has no
--    migration — this creates it with RLS.  Because webhook processing runs
--    under the service-role client (no user session), a service-role-only
--    access pattern is enforced.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. tenants — enable RLS with deny-all for anon/authenticated callers.
--    The app reads/writes tenants exclusively via get_service_role_client()
--    which bypasses RLS.  This prevents any JWT-authenticated caller from
--    reading or enumerating other tenants' rows via the anon key.
-- ---------------------------------------------------------------------------

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

-- Deny-all policy: authenticated users cannot SELECT/INSERT/UPDATE/DELETE
-- tenants rows via the anon or authenticated Postgrest key.
-- Service-role callers bypass RLS entirely (no policy needed for them).
CREATE POLICY "deny_direct_tenant_access" ON tenants
    AS RESTRICTIVE
    USING (false);

-- ---------------------------------------------------------------------------
-- 2. webhook_events — idempotency log for Stripe webhook processing.
--    Written by the application via service-role client only.
--    No direct authenticated-user access needed.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS webhook_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider            TEXT NOT NULL DEFAULT 'stripe',
    provider_event_id   TEXT NOT NULL UNIQUE,
    event_type          TEXT NOT NULL,
    tenant_id           UUID REFERENCES tenants(id) ON DELETE SET NULL,
    processed_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;

-- Deny-all for authenticated callers: webhook_events are an internal audit
-- log accessed only via service-role.
CREATE POLICY "deny_direct_webhook_access" ON webhook_events
    AS RESTRICTIVE
    USING (false);

CREATE INDEX IF NOT EXISTS idx_webhook_events_provider_event
    ON webhook_events(provider_event_id);

CREATE INDEX IF NOT EXISTS idx_webhook_events_tenant
    ON webhook_events(tenant_id, processed_at DESC)
    WHERE tenant_id IS NOT NULL;

COMMIT;
