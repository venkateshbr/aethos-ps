-- Backfill titles for historical Atlas conversations that were left as
-- "New conversation" before thread titles were derived from the first prompt.

WITH first_user_message AS (
    SELECT DISTINCT ON (tenant_id, thread_id)
           tenant_id,
           thread_id,
           LEFT(TRIM(REGEXP_REPLACE(COALESCE(content, ''), '\s+', ' ', 'g')), 80) AS title
      FROM chat_messages
     WHERE role = 'user'
       AND NULLIF(TRIM(REGEXP_REPLACE(COALESCE(content, ''), '\s+', ' ', 'g')), '') IS NOT NULL
     ORDER BY tenant_id, thread_id, created_at ASC
)
UPDATE chat_threads
   SET title = first_user_message.title,
       updated_at = NOW()
  FROM first_user_message
 WHERE chat_threads.id = first_user_message.thread_id
   AND chat_threads.tenant_id = first_user_message.tenant_id
   AND chat_threads.deleted_at IS NULL
   AND (
       chat_threads.title IS NULL
       OR BTRIM(chat_threads.title) = ''
       OR chat_threads.title = 'New conversation'
   );
