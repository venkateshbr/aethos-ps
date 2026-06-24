-- =============================================================================
-- Migration 0057: Accounting Authenticated Read RLS
--
-- Continue service-role reduction for bounded accounting read surfaces. Period
-- locking/unlocking, close packages/readiness, agent proposals, and manual
-- journal posting remain service-role-backed because they reconcile or mutate
-- accounting state.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON period_locks;
DROP POLICY IF EXISTS "authenticated_member_read" ON journal_entries;

CREATE POLICY "authenticated_member_read" ON period_locks
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE POLICY "authenticated_member_read" ON journal_entries
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
