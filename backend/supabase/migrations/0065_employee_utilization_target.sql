-- =============================================================================
-- Migration 0065: Employee billable utilization target
-- =============================================================================
-- Adds an optional resource-planning target used by capacity reports and
-- services-business intelligence queues.
-- =============================================================================

BEGIN;

ALTER TABLE employees
    ADD COLUMN IF NOT EXISTS target_billable_utilization_pct NUMERIC(5,2);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_employees_target_billable_utilization_pct'
    ) THEN
        ALTER TABLE employees
            ADD CONSTRAINT ck_employees_target_billable_utilization_pct
            CHECK (
                target_billable_utilization_pct IS NULL
                OR (
                    target_billable_utilization_pct >= 0
                    AND target_billable_utilization_pct <= 100
                )
            );
    END IF;
END $$;

COMMIT;
