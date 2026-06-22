-- =============================================================================
-- Migration 0046: Projects Authenticated Read RLS
--
-- Continue service-role reduction for project-master read surfaces. Project
-- create/delete and nested assignment/expense mutation paths remain API-gated
-- and service-role backed; authenticated tenant members can read project rows.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON projects;

CREATE POLICY "authenticated_member_read" ON projects
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
