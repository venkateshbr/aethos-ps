-- Keep Atlas conversation history named and sorted by real message activity.
-- The application repository performs the same update on the primary API path;
-- this trigger protects any future worker/import path that appends chat messages.

CREATE OR REPLACE FUNCTION trg_touch_chat_thread_on_message()
RETURNS trigger AS $$
DECLARE
    suggested_title TEXT;
BEGIN
    IF NEW.role = 'user' THEN
        suggested_title := NULLIF(
            LEFT(TRIM(REGEXP_REPLACE(COALESCE(NEW.content, ''), '\s+', ' ', 'g')), 80),
            ''
        );
    END IF;

    UPDATE chat_threads
       SET title = CASE
               WHEN NEW.role = 'user'
                AND suggested_title IS NOT NULL
                AND (
                    title IS NULL
                    OR BTRIM(title) = ''
                    OR title = 'New conversation'
                )
               THEN suggested_title
               ELSE title
           END,
           updated_at = NOW()
     WHERE id = NEW.thread_id
       AND tenant_id = NEW.tenant_id
       AND deleted_at IS NULL;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

DROP TRIGGER IF EXISTS touch_chat_thread_on_message ON chat_messages;
CREATE TRIGGER touch_chat_thread_on_message
    AFTER INSERT ON chat_messages
    FOR EACH ROW EXECUTE FUNCTION trg_touch_chat_thread_on_message();
