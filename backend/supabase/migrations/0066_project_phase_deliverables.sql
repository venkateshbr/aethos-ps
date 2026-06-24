-- =============================================================================
-- Migration 0066: Project Phase Deliverables And Progress
-- =============================================================================
-- Adds launch-demo project planning fields to existing project_phases so phases
-- can double as scheduled milestones/deliverables with progress evidence.
-- =============================================================================

BEGIN;

ALTER TABLE project_phases
    ADD COLUMN IF NOT EXISTS deliverable_name TEXT,
    ADD COLUMN IF NOT EXISTS deliverable_acceptance_criteria TEXT,
    ADD COLUMN IF NOT EXISTS percent_complete NUMERIC(5,2) NOT NULL DEFAULT 0;

DO $$
BEGIN
    ALTER TABLE project_phases
        ADD CONSTRAINT ck_project_phases_percent_complete
        CHECK (percent_complete >= 0 AND percent_complete <= 100);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_project_phases_project_order
    ON project_phases(project_id, order_index)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_project_phases_due_open
    ON project_phases(tenant_id, end_date)
    WHERE deleted_at IS NULL AND status NOT IN ('completed', 'cancelled');

COMMIT;
