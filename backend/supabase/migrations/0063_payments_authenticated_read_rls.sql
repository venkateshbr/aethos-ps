-- =============================================================================
-- Migration 0063: Payments Authenticated Read RLS
--
-- Payment receipt listing is read-only and API-gated. Payment creation remains
-- service-role backed through invoice/manual-payment and Stripe webhook flows.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON payments;

CREATE POLICY "authenticated_member_read" ON payments
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
