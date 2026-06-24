-- =============================================================================
-- Migration 0039: Immutable Financial Event Log
--
-- Adds an append-only, tenant-scoped financial audit spine. Initial trigger
-- coverage records posted journal entries and period lock/unlock actions inside
-- the same database transaction as the source accounting workflow.
-- =============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE period_locks
    ADD COLUMN unlock_requested_by UUID;

-- ---------------------------------------------------------------------------
-- financial_events
-- ---------------------------------------------------------------------------
CREATE TABLE financial_events (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_type              TEXT NOT NULL,
    entity_type             TEXT NOT NULL,
    entity_id               TEXT NOT NULL,
    source_type             TEXT,
    source_id               TEXT,
    actor_user_id           TEXT,
    actor_role              TEXT,
    action                  TEXT NOT NULL,
    before_state            JSONB NOT NULL DEFAULT '{}'::JSONB,
    after_state             JSONB NOT NULL DEFAULT '{}'::JSONB,
    metadata                JSONB NOT NULL DEFAULT '{}'::JSONB,
    idempotency_key         TEXT,
    previous_event_hash     TEXT,
    event_hash              TEXT NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE financial_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON financial_events
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE INDEX idx_financial_events_tenant_created
    ON financial_events(tenant_id, created_at DESC);
CREATE INDEX idx_financial_events_entity
    ON financial_events(tenant_id, entity_type, entity_id, created_at DESC);
CREATE INDEX idx_financial_events_type
    ON financial_events(tenant_id, event_type, created_at DESC);
CREATE UNIQUE INDEX idx_financial_events_idempotency
    ON financial_events(tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
CREATE UNIQUE INDEX idx_financial_events_hash
    ON financial_events(tenant_id, event_hash);

-- ---------------------------------------------------------------------------
-- Immutability guard: financial_events are append-only.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_prevent_financial_event_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RAISE EXCEPTION 'financial_events is immutable'
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$;

CREATE TRIGGER prevent_financial_event_update
    BEFORE UPDATE ON financial_events
    FOR EACH ROW EXECUTE FUNCTION trg_prevent_financial_event_mutation();

CREATE TRIGGER prevent_financial_event_delete
    BEFORE DELETE ON financial_events
    FOR EACH ROW EXECUTE FUNCTION trg_prevent_financial_event_mutation();

-- ---------------------------------------------------------------------------
-- Append helper: computes a tenant-local hash chain.
-- ---------------------------------------------------------------------------
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
SET search_path = public
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

-- ---------------------------------------------------------------------------
-- Journal entry trigger: every posted journal enters the financial event log.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_log_journal_entry_posted_event()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    PERFORM append_financial_event(
        NEW.tenant_id,
        'journal_entry.posted',
        'journal_entry',
        NEW.id::TEXT,
        COALESCE(NEW.reference_type, 'journal_entry'),
        COALESCE(NEW.reference_id::TEXT, NEW.id::TEXT),
        NEW.created_by::TEXT,
        NULL,
        'posted',
        '{}'::JSONB,
        TO_JSONB(NEW),
        jsonb_build_object(
            'entry_number', NEW.entry_number,
            'entry_type', NEW.entry_type,
            'period', NEW.period,
            'reference_type', NEW.reference_type,
            'reference_id', NEW.reference_id
        ),
        'journal_entry.posted:' || NEW.id::TEXT
    );
    RETURN NEW;
END;
$$;

CREATE TRIGGER log_journal_entry_posted_event
    AFTER INSERT ON journal_entries
    FOR EACH ROW
    WHEN (NEW.posted_at IS NOT NULL)
    EXECUTE FUNCTION trg_log_journal_entry_posted_event();

-- ---------------------------------------------------------------------------
-- Period lock triggers: lock and unlock actions are explicitly auditable.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_log_period_locked_event()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    PERFORM append_financial_event(
        NEW.tenant_id,
        'period.locked',
        'period_lock',
        NEW.id::TEXT,
        'period_lock',
        NEW.id::TEXT,
        NEW.locked_by::TEXT,
        NULL,
        'locked',
        '{}'::JSONB,
        TO_JSONB(NEW),
        jsonb_build_object('period', NEW.period),
        'period.locked:' || NEW.id::TEXT
    );
    RETURN NEW;
END;
$$;

CREATE TRIGGER log_period_locked_event
    AFTER INSERT ON period_locks
    FOR EACH ROW EXECUTE FUNCTION trg_log_period_locked_event();

CREATE OR REPLACE FUNCTION trg_log_period_unlocked_event()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    PERFORM append_financial_event(
        OLD.tenant_id,
        'period.unlocked',
        'period_lock',
        OLD.id::TEXT,
        'period_lock',
        OLD.id::TEXT,
        COALESCE(OLD.unlock_requested_by, OLD.locked_by)::TEXT,
        NULL,
        'unlocked',
        TO_JSONB(OLD),
        '{}'::JSONB,
        jsonb_build_object(
            'period', OLD.period,
            'locked_by', OLD.locked_by,
            'unlock_requested_by', OLD.unlock_requested_by
        ),
        'period.unlocked:' || OLD.id::TEXT
    );
    RETURN OLD;
END;
$$;

CREATE TRIGGER log_period_unlocked_event
    AFTER DELETE ON period_locks
    FOR EACH ROW EXECUTE FUNCTION trg_log_period_unlocked_event();

REVOKE ALL ON FUNCTION trg_prevent_financial_event_mutation() FROM PUBLIC;
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
REVOKE ALL ON FUNCTION trg_log_journal_entry_posted_event() FROM PUBLIC;
REVOKE ALL ON FUNCTION trg_log_period_locked_event() FROM PUBLIC;
REVOKE ALL ON FUNCTION trg_log_period_unlocked_event() FROM PUBLIC;

COMMIT;
