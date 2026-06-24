-- =============================================================================
-- Migration 0056: Financial Events Authenticated Read RLS
--
-- Continue service-role reduction for financial audit event read/export
-- surfaces. Financial event writes remain database-trigger and service-role
-- controlled; API access stays admin-gated while using authenticated RLS reads.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON financial_events;

CREATE POLICY "authenticated_member_read" ON financial_events
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
