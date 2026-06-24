-- =============================================================================
-- Migration 0064: Financial Event Hash Search Path
--
-- Supabase installs pgcrypto in the `extensions` schema. Migration 0039 created
-- append_financial_event() with search_path=public, so the trigger could not
-- resolve digest(text, text) when journal entries or period locks were posted.
-- Recreate the helper with extensions on the search path.
-- =============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;

CREATE OR REPLACE FUNCTION append_financial_event(
    p_tenant_id UUID,
    p_event_type TEXT,
    p_entity_type TEXT,
    p_entity_id TEXT,
    p_source_type TEXT,
    p_source_id TEXT,
    p_actor_user_id TEXT,
    p_actor_role TEXT,
    p_action TEXT,
    p_before_state JSONB,
    p_after_state JSONB,
    p_metadata JSONB,
    p_idempotency_key TEXT
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions, pg_temp
AS $$
DECLARE
    v_event_id UUID := gen_random_uuid();
    v_created_at TIMESTAMPTZ := NOW();
    v_previous_event_hash TEXT;
    v_hash_payload JSONB;
    v_event_hash TEXT;
BEGIN
    SELECT event_hash
      INTO v_previous_event_hash
      FROM financial_events
     WHERE tenant_id = p_tenant_id
     ORDER BY created_at DESC, id DESC
     LIMIT 1;

    v_hash_payload := jsonb_build_object(
        'id', v_event_id::TEXT,
        'tenant_id', p_tenant_id::TEXT,
        'event_type', p_event_type,
        'entity_type', p_entity_type,
        'entity_id', p_entity_id,
        'source_type', p_source_type,
        'source_id', p_source_id,
        'actor_user_id', p_actor_user_id,
        'actor_role', p_actor_role,
        'action', p_action,
        'before_state', COALESCE(p_before_state, '{}'::JSONB),
        'after_state', COALESCE(p_after_state, '{}'::JSONB),
        'metadata', COALESCE(p_metadata, '{}'::JSONB),
        'idempotency_key', p_idempotency_key,
        'previous_event_hash', v_previous_event_hash,
        'created_at', v_created_at
    );
    v_event_hash := encode(digest(v_hash_payload::TEXT, 'sha256'), 'hex');

    INSERT INTO financial_events (
        id,
        tenant_id,
        event_type,
        entity_type,
        entity_id,
        source_type,
        source_id,
        actor_user_id,
        actor_role,
        action,
        before_state,
        after_state,
        metadata,
        idempotency_key,
        previous_event_hash,
        event_hash,
        created_at
    )
    VALUES (
        v_event_id,
        p_tenant_id,
        p_event_type,
        p_entity_type,
        p_entity_id,
        p_source_type,
        p_source_id,
        p_actor_user_id,
        p_actor_role,
        p_action,
        COALESCE(p_before_state, '{}'::JSONB),
        COALESCE(p_after_state, '{}'::JSONB),
        COALESCE(p_metadata, '{}'::JSONB),
        p_idempotency_key,
        v_previous_event_hash,
        v_event_hash,
        v_created_at
    );

    RETURN v_event_id;
END;
$$;

REVOKE ALL ON FUNCTION append_financial_event(
    UUID,
    TEXT,
    TEXT,
    TEXT,
    TEXT,
    TEXT,
    TEXT,
    TEXT,
    TEXT,
    JSONB,
    JSONB,
    JSONB,
    TEXT
) FROM PUBLIC;

COMMIT;
