-- =============================================================================
-- Migration 0072: Collections Reminder Policies
--
-- Tenant-level and client-specific dunning policy controls used by the
-- collections worker. Client overrides take precedence over the tenant default.
-- =============================================================================

BEGIN;

CREATE TABLE collections_policies (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id                   UUID REFERENCES clients(id) ON DELETE CASCADE,
    is_enabled                  BOOLEAN NOT NULL DEFAULT TRUE,
    gentle_after_days           INTEGER NOT NULL DEFAULT 1,
    firm_after_days             INTEGER NOT NULL DEFAULT 8,
    final_after_days            INTEGER NOT NULL DEFAULT 31,
    cooldown_days               INTEGER NOT NULL DEFAULT 7,
    max_reminders_per_invoice   INTEGER NOT NULL DEFAULT 3,
    max_auto_send_tone          TEXT NOT NULL DEFAULT 'final',
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at                  TIMESTAMPTZ,

    CONSTRAINT ck_collections_policy_tone_days CHECK (
        gentle_after_days >= 1
        AND firm_after_days >= gentle_after_days
        AND final_after_days >= firm_after_days
    ),
    CONSTRAINT ck_collections_policy_cooldown CHECK (
        cooldown_days BETWEEN 1 AND 365
    ),
    CONSTRAINT ck_collections_policy_max_reminders CHECK (
        max_reminders_per_invoice BETWEEN 1 AND 20
    ),
    CONSTRAINT ck_collections_policy_auto_tone CHECK (
        max_auto_send_tone IN ('none', 'gentle', 'firm', 'final')
    )
);

ALTER TABLE collections_policies ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_isolation" ON collections_policies
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY "authenticated_member_read" ON collections_policies
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE TRIGGER set_updated_at BEFORE UPDATE ON collections_policies
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE UNIQUE INDEX uq_collections_policy_tenant_default
    ON collections_policies (tenant_id)
    WHERE client_id IS NULL AND deleted_at IS NULL;

CREATE UNIQUE INDEX uq_collections_policy_client
    ON collections_policies (tenant_id, client_id)
    WHERE client_id IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX idx_collections_policies_tenant
    ON collections_policies (tenant_id)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_collections_policies_client
    ON collections_policies (tenant_id, client_id)
    WHERE deleted_at IS NULL;

COMMENT ON TABLE collections_policies IS
    'Tenant and client-specific controls for collections reminder cadence, escalation, and auto-send tone limits.';
COMMENT ON COLUMN collections_policies.max_auto_send_tone IS
    'Highest reminder tone the worker may auto-send when autonomy/HITL gates also allow it. none disables auto-send.';

COMMIT;
