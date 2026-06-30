-- =============================================================================
-- Migration 0095: Dedicated approver and auditor roles
--
-- Adds approval-only and audit-only ERP roles without changing existing users.
-- The enum values are not used in this migration, keeping ALTER TYPE safe.
-- =============================================================================

ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'approver';
ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'auditor';

ALTER TABLE tenant_approval_policies
    DROP CONSTRAINT IF EXISTS ck_tenant_approval_policy_roles;

ALTER TABLE tenant_approval_policies
    ADD CONSTRAINT ck_tenant_approval_policy_roles CHECK (
        money_out_default_role IN ('admin', 'owner')
        AND money_out_owner_role = 'owner'
        AND accounting_role IN ('admin', 'owner')
        AND money_in_role IN ('approver', 'manager', 'admin', 'owner')
        AND draft_role IN ('approver', 'manager', 'admin', 'owner')
        AND external_send_role IN ('approver', 'manager', 'admin', 'owner')
        AND high_risk_role IN ('admin', 'owner')
    );
