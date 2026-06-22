-- =============================================================================
-- Migration 0054: Billing Runs Authenticated Read RLS
--
-- Continue service-role reduction for billing-run read surfaces. Creation and
-- approval remain API-gated service-role paths because approval drafts invoices
-- and workers create scheduled runs across tenants.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON billing_runs;

CREATE POLICY "authenticated_member_read" ON billing_runs
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
