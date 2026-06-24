-- =============================================================================
-- Migration 0052: Invoices Authenticated Read RLS
--
-- Continue service-role reduction for AR invoice read surfaces. Invoice draft,
-- create, approval, send, payment, and public-token access remain API-gated
-- service-role paths because they create accounting effects or have no user JWT.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON invoices;
DROP POLICY IF EXISTS "authenticated_member_read" ON invoice_lines;

CREATE POLICY "authenticated_member_read" ON invoices
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE POLICY "authenticated_member_read" ON invoice_lines
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
