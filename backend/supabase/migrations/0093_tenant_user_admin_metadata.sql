-- =============================================================================
-- Migration 0093: Tenant user administration metadata and audit trail
-- =============================================================================
-- Adds product-facing metadata to tenant_users so the ERP can list and manage
-- invited users without reaching into Supabase Auth internals. Also adds an
-- immutable tenant_user_audit_events table for invite, role-change, and
-- deactivation evidence.
-- =============================================================================

BEGIN;

ALTER TABLE tenant_users
    ADD COLUMN IF NOT EXISTS email TEXT,
    ADD COLUMN IF NOT EXISTS display_name TEXT,
    ADD COLUMN IF NOT EXISTS invited_by_user_id UUID,
    ADD COLUMN IF NOT EXISTS deactivated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deactivated_by_user_id UUID;

CREATE UNIQUE INDEX IF NOT EXISTS idx_tenant_users_active_email
    ON tenant_users (tenant_id, lower(email))
    WHERE deleted_at IS NULL AND email IS NOT NULL;

CREATE TABLE IF NOT EXISTS tenant_user_audit_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tenant_user_id      UUID REFERENCES tenant_users(id) ON DELETE SET NULL,
    actor_user_id       UUID,
    action              TEXT NOT NULL CHECK (
        action IN ('invited', 'role_changed', 'profile_updated', 'deactivated', 'reactivated')
    ),
    previous_role       user_role,
    new_role            user_role,
    metadata            JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE tenant_user_audit_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "tenant_isolation" ON tenant_user_audit_events;
CREATE POLICY "tenant_isolation" ON tenant_user_audit_events
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE INDEX IF NOT EXISTS idx_tenant_user_audit_events_tenant_id
    ON tenant_user_audit_events (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tenant_user_audit_events_tenant_user_id
    ON tenant_user_audit_events (tenant_user_id, created_at DESC);

COMMIT;
