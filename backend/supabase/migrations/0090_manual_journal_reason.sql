BEGIN;

ALTER TABLE journal_entries
    ADD COLUMN IF NOT EXISTS reason TEXT;

COMMENT ON COLUMN journal_entries.reason IS
    'Business reason/memo for manual journals; enforced by API for manual postings.';

COMMIT;
