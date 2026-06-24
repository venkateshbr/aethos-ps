-- =============================================================================
-- Migration 0061: Agent Dashboard Authenticated Read RLS
--
-- Agent dashboard reads are API-gated and tenant-scoped. Mutating autonomy
-- controls remain service-role backed because they update policy state.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON agent_autonomy_settings;
DROP POLICY IF EXISTS "authenticated_member_read" ON agent_runs;
DROP POLICY IF EXISTS "authenticated_member_read" ON agent_tool_invocations;
DROP POLICY IF EXISTS "authenticated_member_read" ON agent_eval_candidates;

CREATE POLICY "authenticated_member_read" ON agent_autonomy_settings
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE POLICY "authenticated_member_read" ON agent_runs
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE POLICY "authenticated_member_read" ON agent_tool_invocations
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE POLICY "authenticated_member_read" ON agent_eval_candidates
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
