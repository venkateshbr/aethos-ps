-- =============================================================================
-- Migration 0087: Tenant Approval Policies
--
-- Tenant-configurable approval controls for AI/HITL finance actions. Defaults
-- preserve the first-slice launch policy while allowing tenants to raise review
-- requirements from Manager/Admin to Owner where needed.
-- =============================================================================

BEGIN;

CREATE TABLE tenant_approval_policies (
    tenant_id                       UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    money_out_default_role          TEXT NOT NULL DEFAULT 'admin',
    money_out_owner_threshold       NUMERIC(18, 2) NOT NULL DEFAULT 50000.00,
    money_out_owner_role            TEXT NOT NULL DEFAULT 'owner',
    accounting_role                 TEXT NOT NULL DEFAULT 'admin',
    money_in_role                   TEXT NOT NULL DEFAULT 'manager',
    draft_role                      TEXT NOT NULL DEFAULT 'manager',
    external_send_role              TEXT NOT NULL DEFAULT 'manager',
    high_risk_role                  TEXT NOT NULL DEFAULT 'admin',
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_tenant_approval_policy_roles CHECK (
        money_out_default_role IN ('admin', 'owner')
        AND money_out_owner_role = 'owner'
        AND accounting_role IN ('admin', 'owner')
        AND money_in_role IN ('manager', 'admin', 'owner')
        AND draft_role IN ('manager', 'admin', 'owner')
        AND external_send_role IN ('manager', 'admin', 'owner')
        AND high_risk_role IN ('admin', 'owner')
    ),
    CONSTRAINT ck_tenant_approval_policy_money_out_threshold CHECK (
        money_out_owner_threshold >= 0
    )
);

ALTER TABLE tenant_approval_policies ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_isolation" ON tenant_approval_policies
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY "authenticated_member_read" ON tenant_approval_policies
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE TRIGGER set_updated_at BEFORE UPDATE ON tenant_approval_policies
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

COMMENT ON TABLE tenant_approval_policies IS
    'Tenant-level approval role thresholds for AI/HITL finance actions.';
COMMENT ON COLUMN tenant_approval_policies.money_out_owner_threshold IS
    'Money-out amount at or above this value requires owner review.';

COMMIT;
