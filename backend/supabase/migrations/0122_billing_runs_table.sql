-- =============================================================================
-- Migration 0122: create the missing `billing_runs` table  (issue #492)
--
-- `billing_runs` is read and written by app/repositories/billing_runs_repo.py,
-- app/workers/billing_run_worker.py and app/api/v1/endpoints/billing_runs.py,
-- and migration 0054 adds an RLS policy to it — but no migration ever created
-- it. A database built from this directory therefore aborted at 0054
-- (`CREATE POLICY ... ON billing_runs` on a missing relation), so migrations
-- 0054-0121 never applied and no new environment could be provisioned from
-- source. Production has the table from an out-of-band change.
--
-- Shape follows docs/PLAN.md §4.7 plus the columns the code actually writes.
-- Guarded with IF NOT EXISTS throughout so it is a no-op where the table
-- already exists, and ordered after 0054 so re-running the whole chain works
-- (0054 is made resilient in the same change).
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS billing_runs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name              TEXT NOT NULL,
    period_start      DATE NOT NULL,
    period_end        DATE NOT NULL,
    status            TEXT NOT NULL DEFAULT 'draft'
                          CHECK (status IN ('draft', 'reviewed', 'approved', 'invoiced')),
    created_by_agent  TEXT,
    summary           JSONB,
    engagement_filter JSONB,
    approved_by       UUID,
    approved_at       TIMESTAMPTZ,
    invoiced_at       TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at        TIMESTAMPTZ,
    CONSTRAINT billing_runs_period_order CHECK (period_end >= period_start)
);

CREATE INDEX IF NOT EXISTS ix_billing_runs_tenant_status
    ON billing_runs (tenant_id, status)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_billing_runs_tenant_created
    ON billing_runs (tenant_id, created_at DESC);

ALTER TABLE billing_runs ENABLE ROW LEVEL SECURITY;

-- Same posture as every other tenant table: authenticated members read; writes
-- stay on the service-role API path (workers create runs across tenants and
-- approval drafts invoices).
DROP POLICY IF EXISTS "authenticated_member_read" ON billing_runs;
CREATE POLICY "authenticated_member_read" ON billing_runs
    FOR SELECT
    TO authenticated
    USING (public.is_tenant_member(auth.uid(), tenant_id));

DROP TRIGGER IF EXISTS set_updated_at ON billing_runs;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON billing_runs
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

COMMENT ON TABLE billing_runs IS
    'Pre-bill batches (PLAN §4.7): draft -> reviewed -> approved -> invoiced. '
    'Invoices reference the run via invoices.billing_run_id.';

COMMIT;
