-- =============================================================================
-- Migration 0049: Project Expenses Authenticated Read RLS
--
-- Continue service-role reduction for expense list surfaces. Expense creation
-- remains API-gated and service-role backed; authenticated tenant members can
-- read project expenses through RLS.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON project_expenses;

CREATE POLICY "authenticated_member_read" ON project_expenses
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
