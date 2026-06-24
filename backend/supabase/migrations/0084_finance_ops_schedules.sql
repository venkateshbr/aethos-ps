-- =============================================================================
-- Migration 0084: Scheduled AI Finance Ops Manager
--
-- Tenant-level cadence controls for the scheduled Finance Ops Manager worker.
-- The worker creates reviewed Inbox work plans and escalation notices; it never
-- directly approves invoices, payments, journals, statements, or external sends.
-- =============================================================================

BEGIN;

CREATE TABLE finance_ops_schedules (
    tenant_id                       UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    is_enabled                      BOOLEAN NOT NULL DEFAULT TRUE,
    cadence                         TEXT NOT NULL DEFAULT 'daily',
    run_hour_utc                    INTEGER NOT NULL DEFAULT 7,
    run_weekday_utc                 INTEGER NOT NULL DEFAULT 0,
    timezone                        TEXT NOT NULL DEFAULT 'UTC',
    period_mode                     TEXT NOT NULL DEFAULT 'current_month',
    lookback_limit                  INTEGER NOT NULL DEFAULT 10,
    stale_after_hours               INTEGER NOT NULL DEFAULT 24,
    high_risk_stale_after_hours     INTEGER NOT NULL DEFAULT 4,
    escalation_enabled              BOOLEAN NOT NULL DEFAULT TRUE,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_finance_ops_schedule_cadence CHECK (
        cadence IN ('daily', 'weekly')
    ),
    CONSTRAINT ck_finance_ops_schedule_run_hour CHECK (
        run_hour_utc BETWEEN 0 AND 23
    ),
    CONSTRAINT ck_finance_ops_schedule_weekday CHECK (
        run_weekday_utc BETWEEN 0 AND 6
    ),
    CONSTRAINT ck_finance_ops_schedule_period_mode CHECK (
        period_mode IN ('current_month', 'previous_month')
    ),
    CONSTRAINT ck_finance_ops_schedule_lookback CHECK (
        lookback_limit BETWEEN 1 AND 25
    ),
    CONSTRAINT ck_finance_ops_schedule_stale_thresholds CHECK (
        high_risk_stale_after_hours BETWEEN 1 AND 720
        AND stale_after_hours BETWEEN high_risk_stale_after_hours AND 720
    )
);

ALTER TABLE finance_ops_schedules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_isolation" ON finance_ops_schedules
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY "authenticated_member_read" ON finance_ops_schedules
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE TRIGGER set_updated_at BEFORE UPDATE ON finance_ops_schedules
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_finance_ops_schedules_enabled
    ON finance_ops_schedules (is_enabled, cadence, run_hour_utc);

COMMENT ON TABLE finance_ops_schedules IS
    'Tenant cadence controls for the scheduled AI Finance Ops Manager.';
COMMENT ON COLUMN finance_ops_schedules.period_mode IS
    'current_month or previous_month period used when building the command-center action plan.';
COMMENT ON COLUMN finance_ops_schedules.escalation_enabled IS
    'When true, the scheduled worker creates non-destructive Inbox escalation notices for stale or high-risk tasks.';

COMMIT;
