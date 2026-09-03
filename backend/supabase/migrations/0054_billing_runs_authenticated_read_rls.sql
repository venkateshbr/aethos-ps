-- =============================================================================
-- Migration 0054: Billing Runs Authenticated Read RLS
--
-- Continue service-role reduction for billing-run read surfaces. Creation and
-- approval remain API-gated service-role paths because approval drafts invoices
-- and workers create scheduled runs across tenants.
-- =============================================================================

BEGIN;

-- #492: `billing_runs` had no CREATE TABLE migration, so applying this file to
-- a fresh database aborted the whole chain here. Migration 0122 now creates the
-- table (and this policy). Skip when the relation does not exist yet so the
-- chain stays applicable in original order.
DO $$
BEGIN
    IF to_regclass('public.billing_runs') IS NULL THEN
        RAISE NOTICE 'billing_runs not present yet; policy created by migration 0122';
        RETURN;
    END IF;

    DROP POLICY IF EXISTS "authenticated_member_read" ON billing_runs;

    CREATE POLICY "authenticated_member_read" ON billing_runs
        FOR SELECT
        TO authenticated
        USING (
            public.is_tenant_member(auth.uid(), tenant_id)
        );
END $$;

COMMIT;
