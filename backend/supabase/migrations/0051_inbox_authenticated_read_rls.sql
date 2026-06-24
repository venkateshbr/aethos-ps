-- =============================================================================
-- Migration 0051: Inbox Authenticated Read RLS
--
-- Continue service-role reduction for HITL inbox read surfaces. Inbox actions
-- remain API-gated and service-role backed because approval/rejection can
-- materialise business mutations and correction/eval records.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON hitl_tasks;
DROP POLICY IF EXISTS "authenticated_member_read" ON agent_suggestions;

CREATE POLICY "authenticated_member_read" ON hitl_tasks
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE POLICY "authenticated_member_read" ON agent_suggestions
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
