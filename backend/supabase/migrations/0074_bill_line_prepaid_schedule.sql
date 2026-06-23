-- =============================================================================
-- Migration 0074: Bill Line Prepaid Expense Schedule
-- =============================================================================
-- Lets AP bill lines carry prepaid-expense treatment and a service window.
-- Approval capitalizes those lines to 1500 Prepaid Expenses; month-end close
-- agents amortize them back to expense over the service period.
-- =============================================================================

BEGIN;

ALTER TABLE bill_lines
    ADD COLUMN IF NOT EXISTS is_prepaid BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS service_start_date DATE,
    ADD COLUMN IF NOT EXISTS service_end_date DATE;

DO $$
BEGIN
    ALTER TABLE bill_lines
        ADD CONSTRAINT ck_bill_lines_prepaid_service_window
        CHECK (
            (
                is_prepaid = FALSE
                AND service_start_date IS NULL
                AND service_end_date IS NULL
            )
            OR (
                is_prepaid = TRUE
                AND service_start_date IS NOT NULL
                AND service_end_date IS NOT NULL
                AND service_end_date >= service_start_date
            )
        );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_bill_lines_prepaid_schedule
    ON bill_lines(tenant_id, service_start_date, service_end_date)
    WHERE is_prepaid = TRUE;

COMMIT;
