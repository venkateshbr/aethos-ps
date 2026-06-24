-- =============================================================================
-- Migration 0043: Service Catalogue Authenticated Read RLS
--
-- Continue service-role reduction for read-only settings/catalogue surfaces.
-- Service catalogue writes remain API-gated and service-role backed for now;
-- read routes can use an anon-key client carrying the caller's JWT.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON service_catalogue;

CREATE POLICY "authenticated_member_read" ON service_catalogue
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
