-- =============================================================================
-- Migration 0088: Accounting Close Override Actor Role
--
-- Preserve the approver's role on close override records so close evidence can
-- show who overrode a blocker and under which governance authority.
-- =============================================================================

BEGIN;

ALTER TABLE accounting_close_overrides
    ADD COLUMN IF NOT EXISTS created_by_role TEXT NOT NULL DEFAULT 'unknown';

COMMENT ON COLUMN accounting_close_overrides.created_by_role IS
    'Application role held by the actor when the close override was recorded.';

COMMIT;
