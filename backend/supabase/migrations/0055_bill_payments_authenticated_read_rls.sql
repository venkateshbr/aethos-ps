-- =============================================================================
-- Migration 0055: Bill Payments Authenticated Read RLS
--
-- Continue service-role reduction for bill-payment batch read surfaces. Batch
-- creation, approval, export, send, settlement, and proposal workflows remain
-- API-gated service-role paths because they validate money-out state, persist
-- export integrity metadata, or post settlement journals.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON bill_payment_batches;
DROP POLICY IF EXISTS "authenticated_member_read" ON bill_payment_items;

CREATE POLICY "authenticated_member_read" ON bill_payment_batches
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE POLICY "authenticated_member_read" ON bill_payment_items
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
