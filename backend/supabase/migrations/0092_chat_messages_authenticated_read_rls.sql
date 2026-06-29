-- =============================================================================
-- Migration 0092: Chat Message Authenticated Read RLS
--
-- Chat message history is loaded through the authenticated RLS client while
-- writes remain service-role backed. Match thread reads: a user may read only
-- messages from their own non-deleted threads inside an active tenant.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_owner_read" ON chat_messages;

CREATE POLICY "authenticated_owner_read" ON chat_messages
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
        AND EXISTS (
            SELECT 1
            FROM chat_threads
            WHERE chat_threads.id = chat_messages.thread_id
              AND chat_threads.tenant_id = chat_messages.tenant_id
              AND chat_threads.user_id = auth.uid()
              AND chat_threads.deleted_at IS NULL
        )
    );

COMMIT;
