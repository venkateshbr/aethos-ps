-- =============================================================================
-- Migration 0011: Project Phases — sub-structure for projects
-- =============================================================================
-- Adds:
--   * phase_status enum
--   * project_phases table — ordered phases within a project
--   * phase_id FK on time_entries  (nullable)
--   * phase_id FK on project_assignments (nullable)
--
-- Money: NUMERIC(15,2). Timestamps: TIMESTAMPTZ.
-- RLS on all tenant-scoped tables.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Enum
-- ---------------------------------------------------------------------------
CREATE TYPE phase_status AS ENUM (
    'planning',
    'active',
    'completed',
    'cancelled'
);

-- ---------------------------------------------------------------------------
-- project_phases
-- Ordered phases within a project.  order_index controls display sequence.
-- budget is optional; agents may suggest per-phase budgets.
-- ---------------------------------------------------------------------------
CREATE TABLE project_phases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    description     TEXT,
    status          phase_status NOT NULL DEFAULT 'planning',
    start_date      DATE,
    end_date        DATE,
    budget          NUMERIC(15,2),
    -- Display / sort order within the project
    order_index     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    CONSTRAINT ck_pp_budget_pos CHECK (budget IS NULL OR budget >= 0),
    CONSTRAINT ck_pp_dates      CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

ALTER TABLE project_phases ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON project_phases
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON project_phases
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_project_phases_project_id ON project_phases(project_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_project_phases_tenant_id  ON project_phases(tenant_id)  WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- Add phase_id to time_entries and project_assignments
-- Both are nullable — existing rows without a phase are valid.
-- ---------------------------------------------------------------------------
ALTER TABLE time_entries
    ADD COLUMN phase_id UUID REFERENCES project_phases(id) ON DELETE SET NULL;

CREATE INDEX idx_te_phase_id ON time_entries(phase_id) WHERE phase_id IS NOT NULL;

ALTER TABLE project_assignments
    ADD COLUMN phase_id UUID REFERENCES project_phases(id) ON DELETE SET NULL;

CREATE INDEX idx_pa_phase_id ON project_assignments(phase_id) WHERE phase_id IS NOT NULL;

COMMIT;
