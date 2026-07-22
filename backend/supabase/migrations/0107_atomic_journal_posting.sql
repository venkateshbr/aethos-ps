-- =============================================================================
-- Migration 0107: Atomic, idempotent journal posting (ADR 0001 / issue #390 / LR-08)
--
-- Replaces the two-insert post_journal path (header + lines as separate PostgREST
-- transactions) with a single atomic RPC, plus two DB-level invariants that hold
-- regardless of how many API nodes post:
--   1. post_journal_entry() inserts header + all lines in ONE transaction.
--   2. A DEFERRABLE constraint trigger enforces debits == credits at commit.
--   3. An idempotency_key unique index makes retries/double-submits exactly-once.
-- Idempotent migration (safe to re-apply via the VPS migrate service).
-- =============================================================================

BEGIN;

-- 1. Idempotency key ---------------------------------------------------------
ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
-- NULLs are distinct in a unique index, so existing rows (NULL) never conflict;
-- new posts always supply a non-null key which is then unique per row.
CREATE UNIQUE INDEX IF NOT EXISTS ux_journal_entries_idempotency_key
    ON journal_entries (idempotency_key);

-- 2. DB-level balance guarantee (cross-row → deferred constraint trigger) -----
CREATE OR REPLACE FUNCTION assert_journal_entry_balanced()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_entry_id UUID := COALESCE(NEW.journal_entry_id, OLD.journal_entry_id);
    v_diff NUMERIC;
BEGIN
    SELECT COALESCE(SUM(
        CASE WHEN direction = 'DR' THEN base_amount ELSE -base_amount END
    ), 0)
      INTO v_diff
      FROM journal_lines
     WHERE journal_entry_id = v_entry_id;

    IF ABS(v_diff) > 0.01 THEN
        RAISE EXCEPTION 'journal_entry % is unbalanced: DR-CR base difference = %',
            v_entry_id, v_diff
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NULL;
END $$;

DROP TRIGGER IF EXISTS trg_journal_entry_balanced ON journal_lines;
CREATE CONSTRAINT TRIGGER trg_journal_entry_balanced
    AFTER INSERT OR UPDATE OR DELETE ON journal_lines
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION assert_journal_entry_balanced();

-- 3. Atomic, idempotent posting RPC ------------------------------------------
CREATE OR REPLACE FUNCTION post_journal_entry(
    p_entry JSONB,
    p_lines JSONB,
    p_idempotency_key TEXT
)
RETURNS JSONB LANGUAGE plpgsql AS $$
DECLARE
    v_id UUID;
    v_entry JSONB;
BEGIN
    -- Fast idempotent path: already posted under this key → return it.
    IF p_idempotency_key IS NOT NULL THEN
        SELECT to_jsonb(je) INTO v_entry
          FROM journal_entries je
         WHERE je.idempotency_key = p_idempotency_key;
        IF v_entry IS NOT NULL THEN
            RETURN jsonb_build_object('entry', v_entry, 'idempotent_hit', true);
        END IF;
    END IF;

    INSERT INTO journal_entries (
        tenant_id, entry_number, entry_type, original_entry_id, description,
        entry_date, period, reference_type, reference_id, posted_at, created_by,
        reason, idempotency_key
    )
    SELECT
        (p_entry->>'tenant_id')::UUID,
        p_entry->>'entry_number',
        COALESCE(p_entry->>'entry_type', 'auto'),
        NULLIF(p_entry->>'original_entry_id', '')::UUID,
        p_entry->>'description',
        (p_entry->>'entry_date')::DATE,
        COALESCE(p_entry->>'period', LEFT(p_entry->>'entry_date', 7)),
        p_entry->>'reference_type',
        NULLIF(p_entry->>'reference_id', '')::UUID,
        COALESCE((p_entry->>'posted_at')::TIMESTAMPTZ, now()),
        NULLIF(p_entry->>'created_by', '')::UUID,
        p_entry->>'reason',
        p_idempotency_key
    ON CONFLICT (idempotency_key) DO NOTHING
    RETURNING id INTO v_id;

    -- Concurrent poster won the race under the same key → return theirs.
    IF v_id IS NULL THEN
        SELECT to_jsonb(je) INTO v_entry
          FROM journal_entries je
         WHERE je.idempotency_key = p_idempotency_key;
        RETURN jsonb_build_object('entry', v_entry, 'idempotent_hit', true);
    END IF;

    INSERT INTO journal_lines (
        tenant_id, journal_entry_id, direction, account_id, amount, currency,
        base_amount, fx_rate_id, description
    )
    SELECT
        (l->>'tenant_id')::UUID,
        v_id,
        l->>'direction',
        NULLIF(l->>'account_id', '')::UUID,
        (l->>'amount')::NUMERIC,
        l->>'currency',
        (l->>'base_amount')::NUMERIC,
        NULLIF(l->>'fx_rate_id', '')::UUID,
        l->>'description'
      FROM jsonb_array_elements(p_lines) AS l;

    -- Deferred balance trigger validates at COMMIT.
    SELECT to_jsonb(je) INTO v_entry FROM journal_entries je WHERE je.id = v_id;
    RETURN jsonb_build_object('entry', v_entry, 'idempotent_hit', false);
END $$;

COMMENT ON FUNCTION post_journal_entry(JSONB, JSONB, TEXT) IS
    'Atomic, idempotent GL posting: inserts header + lines in one transaction, '
    'deduped on idempotency_key; balance is enforced by trg_journal_entry_balanced.';

COMMIT;
