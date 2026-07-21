-- =============================================================================
-- Migration 0109: Configurable automation schedules (Background Jobs Console)
--
-- Generalizes the finance-ops cadence pattern (migration 0084) to the other
-- tenant-facing recurring jobs so a tenant admin can enable/disable each one and
-- set when it runs. The periodic workers already sweep tenants hourly; they now
-- consult this table (via automation_schedules_service) to decide what is due,
-- exactly as finance_ops_manager_worker consults finance_ops_schedules.
--
-- Scope note: finance_ops keeps its own richer table (finance_ops_schedules).
-- Platform-global jobs (fx_refresh, autonomy_promoter) are operator-controlled,
-- not per-tenant, so they are intentionally not in this tenant-scoped table.
-- =============================================================================

BEGIN;

CREATE TABLE automation_schedules (
    tenant_id       UUID    NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    job_key         TEXT    NOT NULL,
    is_enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    cadence         TEXT    NOT NULL DEFAULT 'daily',
    run_hour_utc    INTEGER NOT NULL DEFAULT 7,
    run_weekday_utc INTEGER NOT NULL DEFAULT 0,
    timezone        TEXT    NOT NULL DEFAULT 'UTC',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (tenant_id, job_key),

    CONSTRAINT ck_automation_schedule_job_key CHECK (
        job_key IN ('collections', 'billing_run', 'close_prep', 'project_health', 'time_reminder')
    ),
    CONSTRAINT ck_automation_schedule_cadence CHECK (cadence IN ('daily', 'weekly', 'monthly')),
    CONSTRAINT ck_automation_schedule_run_hour CHECK (run_hour_utc BETWEEN 0 AND 23),
    CONSTRAINT ck_automation_schedule_weekday CHECK (run_weekday_utc BETWEEN 0 AND 6)
);

ALTER TABLE automation_schedules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_isolation" ON automation_schedules
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY "authenticated_member_read" ON automation_schedules
    FOR SELECT
    TO authenticated
    USING (public.is_tenant_member(auth.uid(), tenant_id));

CREATE TRIGGER set_updated_at BEFORE UPDATE ON automation_schedules
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_automation_schedules_enabled
    ON automation_schedules (job_key, is_enabled, cadence, run_hour_utc);

COMMENT ON TABLE automation_schedules IS
    'Per-tenant enable/disable + cadence for recurring background jobs, read by the '
    'periodic workers to decide what is due. Complements finance_ops_schedules.';
COMMENT ON COLUMN automation_schedules.job_key IS
    'Which recurring job this row configures (collections, billing_run, close_prep, project_health, time_reminder).';

COMMIT;
