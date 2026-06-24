-- =============================================================================
-- Migration 0060: Reports Authenticated Read RLS
--
-- Reports are read-only API surfaces. Most source tables already have
-- authenticated tenant-member SELECT policies from earlier service-role
-- reduction slices; this adds the remaining report-only tables.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON journal_lines;
DROP POLICY IF EXISTS "authenticated_member_read" ON project_assignments;

CREATE POLICY "authenticated_member_read" ON journal_lines
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE POLICY "authenticated_member_read" ON project_assignments
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
