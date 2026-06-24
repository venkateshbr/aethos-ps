-- =============================================================================
-- Migration 0042: Tax Rates Authenticated Read RLS
--
-- Continue service-role reduction for read-only settings surfaces. System tax
-- rates remain readable as seeded reference data; tenant custom rates are
-- readable to authenticated tenant members through is_tenant_member().
-- Create/update paths stay API-gated and service-role backed for now.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON tax_rates;

CREATE POLICY "authenticated_member_read" ON tax_rates
    FOR SELECT
    TO authenticated
    USING (
        tenant_id IS NULL
        OR public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
