-- =============================================================================
-- Migration 0113: Posted-journal completeness + tenant consistency (issue #372)
--
-- Migration 0107 gave us an atomic posting RPC, an idempotency_key unique index,
-- and a DEFERRABLE balance trigger on journal_lines. That balance trigger fires
-- on line INSERT/UPDATE/DELETE, so it validates entries that HAVE lines — but it
-- never fires for a POSTED header with **zero lines**, and it does not assert
-- that every line belongs to the same tenant as its header (#372 AC-2 / AC-5).
--
-- This migration adds a per-entry DEFERRABLE constraint trigger on
-- journal_entries that, at COMMIT, requires every *posted* entry (posted_at IS
-- NOT NULL) to have >= 1 line, to balance in base currency, and to have no line
-- owned by another tenant. Drafts (posted_at IS NULL) are exempt — they may be
-- empty/unbalanced while being built. It only validates rows written from now on
-- (existing data is audited separately via scripts/audit_journal_integrity.py,
-- #372 AC-7). Idempotent — safe to re-apply via the VPS migrate service.
-- =============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION assert_posted_journal_entry_complete()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_line_count     INT;
    v_diff           NUMERIC;
    v_foreign_tenant INT;
BEGIN
    -- Only posted entries must be complete; drafts may be empty/unbalanced.
    IF NEW.posted_at IS NULL THEN
        RETURN NULL;
    END IF;

    SELECT
        COUNT(*),
        COALESCE(SUM(CASE WHEN direction = 'DR' THEN base_amount ELSE -base_amount END), 0),
        COUNT(*) FILTER (WHERE tenant_id IS DISTINCT FROM NEW.tenant_id)
      INTO v_line_count, v_diff, v_foreign_tenant
      FROM journal_lines
     WHERE journal_entry_id = NEW.id;

    IF v_line_count = 0 THEN
        RAISE EXCEPTION 'posted journal_entry % has no lines', NEW.id
            USING ERRCODE = 'check_violation';
    END IF;

    IF ABS(v_diff) > 0.01 THEN
        RAISE EXCEPTION 'posted journal_entry % is unbalanced: DR-CR base difference = %',
            NEW.id, v_diff
            USING ERRCODE = 'check_violation';
    END IF;

    IF v_foreign_tenant > 0 THEN
        RAISE EXCEPTION 'posted journal_entry % has % line(s) belonging to another tenant',
            NEW.id, v_foreign_tenant
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NULL;
END $$;

-- Fires per entry, deferred to COMMIT so the RPC's header-then-lines insert order
-- is valid. Covers both the atomic-RPC INSERT path and any draft -> posted UPDATE.
DROP TRIGGER IF EXISTS trg_posted_journal_entry_complete ON journal_entries;
CREATE CONSTRAINT TRIGGER trg_posted_journal_entry_complete
    AFTER INSERT OR UPDATE ON journal_entries
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION assert_posted_journal_entry_complete();

COMMENT ON FUNCTION assert_posted_journal_entry_complete() IS
    'Deferred per-entry invariant for posted journals (#372): >= 1 line, balanced '
    'in base currency, and all lines owned by the header tenant. Drafts exempt.';

COMMIT;
