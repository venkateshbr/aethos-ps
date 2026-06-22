-- =============================================================================
-- Migration 0045: Employees Authenticated Read RLS
--
-- Continue service-role reduction for people-master read surfaces. Employee
-- writes, soft deletes, and invite workflows remain API-gated and service-role
-- backed; authenticated tenant members can read employee rows through RLS.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON employees;

CREATE POLICY "authenticated_member_read" ON employees
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
