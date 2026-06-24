-- =============================================================================
-- Migration 0086: Accounting Close Overrides
--
-- Records explicit controller/admin overrides for month-end close blockers.
-- These rows make override reasons, actors, timestamps, and blocker evidence
-- visible in close packages and enforceable by the period-lock API.
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS accounting_close_overrides (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    period          TEXT NOT NULL,
    blocker_code    TEXT NOT NULL,
    blocker_ref     JSONB NOT NULL DEFAULT '{}'::jsonb,
    reason          TEXT NOT NULL,
    created_by      TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    CONSTRAINT ck_aco_period_format CHECK (period ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    CONSTRAINT ck_aco_reason_present CHECK (char_length(btrim(reason)) >= 10),
    CONSTRAINT ck_aco_blocker_code CHECK (
        blocker_code IN (
            'subledger_reconciliation',
            'trial_balance',
            'close_reviews',
            'close_tasks',
            'unposted_journals'
        )
    )
);

ALTER TABLE accounting_close_overrides ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "tenant_isolation" ON accounting_close_overrides;
CREATE POLICY "tenant_isolation" ON accounting_close_overrides
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

DROP POLICY IF EXISTS "authenticated_member_read" ON accounting_close_overrides;
CREATE POLICY "authenticated_member_read" ON accounting_close_overrides
    FOR SELECT
    TO authenticated
    USING (public.is_tenant_member(auth.uid(), tenant_id));

CREATE INDEX IF NOT EXISTS idx_accounting_close_overrides_period
    ON accounting_close_overrides(tenant_id, period, blocker_code, created_at DESC)
    WHERE deleted_at IS NULL;

COMMIT;
