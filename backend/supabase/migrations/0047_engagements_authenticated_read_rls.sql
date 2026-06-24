-- =============================================================================
-- Migration 0047: Engagements Authenticated Read RLS
--
-- Continue service-role reduction for engagement-master read surfaces. Simple
-- list/detail reads need engagements plus engagement_billing_terms; summary and
-- invoice-draft paths still read broader financial/time data through API-gated
-- service-role paths until those aggregates receive full RLS coverage.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON engagements;
DROP POLICY IF EXISTS "authenticated_member_read" ON engagement_billing_terms;

CREATE POLICY "authenticated_member_read" ON engagements
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE POLICY "authenticated_member_read" ON engagement_billing_terms
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
