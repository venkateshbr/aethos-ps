-- =============================================================================
-- Migration 0053: Bills Authenticated Read RLS
--
-- Continue service-role reduction for AP bill read surfaces. Bill creation,
-- approval, voiding, and payment workflows remain API-gated service-role paths
-- because they validate vendor/account state, post journals, or mutate ledgers.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON bills;
DROP POLICY IF EXISTS "authenticated_member_read" ON bill_lines;

CREATE POLICY "authenticated_member_read" ON bills
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE POLICY "authenticated_member_read" ON bill_lines
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
