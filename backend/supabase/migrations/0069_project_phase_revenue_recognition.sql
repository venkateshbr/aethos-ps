-- =============================================================================
-- Migration 0069: Project Phase Revenue Recognition Amount
-- =============================================================================
-- Adds a revenue-specific milestone amount to project_phases. This keeps
-- delivery budgets separate from the amount that should be recognized when a
-- milestone is accepted/completed.
-- =============================================================================

BEGIN;

ALTER TABLE project_phases
    ADD COLUMN IF NOT EXISTS revenue_recognition_amount NUMERIC(15,2);

DO $$
BEGIN
    ALTER TABLE project_phases
        ADD CONSTRAINT ck_project_phases_revenue_recognition_amount
        CHECK (
            revenue_recognition_amount IS NULL
            OR revenue_recognition_amount >= 0
        );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_project_phases_recognition_ready
    ON project_phases(tenant_id, end_date)
    WHERE deleted_at IS NULL
      AND status = 'completed'
      AND revenue_recognition_amount IS NOT NULL;

COMMIT;
