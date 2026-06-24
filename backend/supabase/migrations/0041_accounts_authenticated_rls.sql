-- =============================================================================
-- Migration 0041: Accounts Authenticated RLS
--
-- First service-role reduction slice.  Keep the existing app.current_tenant_id
-- path for internal/service-role workflows, and add an authenticated-member path
-- so GET /accounts can use an anon-key client carrying the caller's JWT.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "tenant_isolation" ON accounts;
DROP POLICY IF EXISTS "authenticated_member_read" ON accounts;

CREATE POLICY "tenant_isolation" ON accounts
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY "authenticated_member_read" ON accounts
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
