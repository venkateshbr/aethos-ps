-- =============================================================================
-- Migration 0068: Accounting Close Tasks
-- =============================================================================
-- Persisted month-end close checklist tasks by tenant/period. These tasks turn
-- the derived close readiness APIs into a guided workflow without duplicating
-- reconciliation evidence.
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS accounting_close_tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    period          TEXT NOT NULL,
    code            TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    owner_role      TEXT NOT NULL DEFAULT 'finance_manager',
    status          TEXT NOT NULL DEFAULT 'open',
    due_date        DATE,
    completed_at    TIMESTAMPTZ,
    completed_by    TEXT,
    evidence        JSONB NOT NULL DEFAULT '{}'::jsonb,
    order_index     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    UNIQUE (tenant_id, period, code),
    CONSTRAINT ck_act_period_format CHECK (period ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    CONSTRAINT ck_act_status CHECK (
        status IN ('open', 'in_progress', 'done', 'waived', 'blocked')
    )
);

ALTER TABLE accounting_close_tasks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "tenant_isolation" ON accounting_close_tasks;
CREATE POLICY "tenant_isolation" ON accounting_close_tasks
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

DROP POLICY IF EXISTS "authenticated_member_read" ON accounting_close_tasks;
CREATE POLICY "authenticated_member_read" ON accounting_close_tasks
    FOR SELECT
    TO authenticated
    USING (public.is_tenant_member(auth.uid(), tenant_id));

CREATE TRIGGER set_updated_at BEFORE UPDATE ON accounting_close_tasks
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX IF NOT EXISTS idx_accounting_close_tasks_period
    ON accounting_close_tasks(tenant_id, period, order_index)
    WHERE deleted_at IS NULL;

COMMIT;
