-- =============================================================================
-- Migration 0062: Chat Thread Authenticated Read RLS
--
-- Chat thread listing is user-scoped at the API layer and now runs through the
-- authenticated RLS client. Writes remain service-role backed.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_owner_read" ON chat_threads;

CREATE POLICY "authenticated_owner_read" ON chat_threads
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
        AND user_id = auth.uid()
    );

COMMIT;
