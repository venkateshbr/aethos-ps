-- Retire empty Atlas threads created by the old eager "New chat" behavior.
-- Conversations with at least one persisted message are preserved.

UPDATE chat_threads
   SET deleted_at = NOW(),
       updated_at = NOW()
 WHERE deleted_at IS NULL
   AND NOT EXISTS (
       SELECT 1
         FROM chat_messages
        WHERE chat_messages.thread_id = chat_threads.id
          AND chat_messages.tenant_id = chat_threads.tenant_id
   );
