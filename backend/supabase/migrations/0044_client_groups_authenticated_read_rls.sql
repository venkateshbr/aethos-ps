-- =============================================================================
-- Migration 0044: Client Groups Authenticated Read RLS
--
-- Continue service-role reduction for related-client read surfaces. Client
-- group reads need client_groups, client_group_members, and clients for member
-- joins; all policies are SELECT-only for authenticated tenant members.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON clients;
DROP POLICY IF EXISTS "authenticated_member_read" ON client_groups;
DROP POLICY IF EXISTS "authenticated_member_read" ON client_group_members;

CREATE POLICY "authenticated_member_read" ON clients
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE POLICY "authenticated_member_read" ON client_groups
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE POLICY "authenticated_member_read" ON client_group_members
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
