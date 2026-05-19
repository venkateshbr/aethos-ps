-- =============================================================================
-- Migration 0005: Documents, Agent Suggestions, HITL Tasks, Corrections,
--                 and Autonomy Settings
-- =============================================================================
-- The AI/HITL layer sits on top of core ERP tables.  Two-table pattern:
--   * agent_suggestions  — immutable AI output record
--   * hitl_tasks         — human-facing work queue item (with assignment, priority)
-- One suggestion may spawn many tasks (e.g. billing run → N invoice tasks).
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
CREATE TYPE document_status AS ENUM ('uploaded', 'extracting', 'extracted', 'failed');

CREATE TYPE agent_suggestion_status AS ENUM (
    'pending',
    'approved',
    'approved_with_edits',
    'rejected',
    'auto_applied',
    'expired'
);

CREATE TYPE hitl_task_status AS ENUM ('open', 'in_progress', 'done', 'expired');
CREATE TYPE hitl_task_priority AS ENUM ('low', 'med', 'high', 'critical');

CREATE TYPE agent_correction_type AS ENUM ('edit', 'reject');

-- ---------------------------------------------------------------------------
-- documents
-- ---------------------------------------------------------------------------
CREATE TABLE documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    uploader_id         UUID NOT NULL,
    -- Populated once extraction agent classifies the document
    document_type       TEXT,
    original_filename   TEXT,
    storage_path        TEXT NOT NULL,
    mime_type           TEXT NOT NULL,
    file_size_bytes     BIGINT,
    sha256              TEXT,
    page_count          INTEGER,
    -- Optional linkage to a business entity after extraction
    entity_type         TEXT,
    entity_id           UUID,
    status              document_status NOT NULL DEFAULT 'uploaded',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON documents
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_documents_tenant_id ON documents(tenant_id);
CREATE INDEX idx_documents_status    ON documents(tenant_id, status);
CREATE INDEX idx_documents_sha256    ON documents(tenant_id, sha256);

-- ---------------------------------------------------------------------------
-- agent_suggestions
-- Immutable AI output record.  status transitions only; payload never changes.
-- ---------------------------------------------------------------------------
CREATE TABLE agent_suggestions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_name              TEXT NOT NULL,
    action_type             TEXT NOT NULL,
    -- Snapshot of what the agent received (PII masked before storage)
    input_snapshot          JSONB NOT NULL DEFAULT '{}'::JSONB,
    -- Structured agent output
    output_snapshot         JSONB NOT NULL DEFAULT '{}'::JSONB,
    confidence              NUMERIC(3,2) NOT NULL,
    status                  agent_suggestion_status NOT NULL DEFAULT 'pending',
    hitl_required           BOOLEAN NOT NULL DEFAULT TRUE,
    -- Source document (if triggered by a doc upload)
    original_document_id    UUID REFERENCES documents(id),
    -- Related business entity (invoice, engagement, bill, …)
    related_entity_type     TEXT,
    related_entity_id       UUID,
    -- Decision tracking
    decided_by              UUID,
    decided_at              TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_agent_suggestion_confidence CHECK (confidence BETWEEN 0 AND 1)
);

ALTER TABLE agent_suggestions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON agent_suggestions
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON agent_suggestions
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_agent_suggestions_tenant_id ON agent_suggestions(tenant_id);
CREATE INDEX idx_agent_suggestions_status    ON agent_suggestions(tenant_id, status);
CREATE INDEX idx_agent_suggestions_agent     ON agent_suggestions(tenant_id, agent_name, action_type);
CREATE INDEX idx_agent_suggestions_document  ON agent_suggestions(original_document_id) WHERE original_document_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- hitl_tasks
-- Human-facing work queue.  Multiple tasks can reference one suggestion.
-- ---------------------------------------------------------------------------
CREATE TABLE hitl_tasks (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_suggestion_id     UUID REFERENCES agent_suggestions(id),
    kind                    TEXT NOT NULL,
    priority                hitl_task_priority NOT NULL DEFAULT 'med',
    assigned_to             UUID,
    title                   TEXT NOT NULL,
    description             TEXT,
    payload                 JSONB NOT NULL DEFAULT '{}'::JSONB,
    status                  hitl_task_status NOT NULL DEFAULT 'open',
    due_at                  TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE hitl_tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON hitl_tasks
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON hitl_tasks
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_hitl_tasks_tenant_id    ON hitl_tasks(tenant_id);
CREATE INDEX idx_hitl_tasks_status       ON hitl_tasks(tenant_id, status);
CREATE INDEX idx_hitl_tasks_assigned_to  ON hitl_tasks(tenant_id, assigned_to) WHERE assigned_to IS NOT NULL;
CREATE INDEX idx_hitl_tasks_due_at       ON hitl_tasks(tenant_id, due_at) WHERE status = 'open';
CREATE INDEX idx_hitl_tasks_suggestion   ON hitl_tasks(agent_suggestion_id) WHERE agent_suggestion_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- agent_corrections
-- Append-only training signal.  Each edit/rejection is recorded for re-training.
-- ---------------------------------------------------------------------------
CREATE TABLE agent_corrections (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_suggestion_id     UUID NOT NULL REFERENCES agent_suggestions(id),
    agent_name              TEXT NOT NULL,
    action_type             TEXT NOT NULL,
    -- What the agent originally output (snapshot at time of correction)
    original_output         JSONB NOT NULL DEFAULT '{}'::JSONB,
    -- What the human changed it to
    corrected_output        JSONB NOT NULL DEFAULT '{}'::JSONB,
    correction_type         agent_correction_type NOT NULL,
    corrected_by            UUID NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- No updated_at — corrections are immutable once recorded
);

ALTER TABLE agent_corrections ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON agent_corrections
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE INDEX idx_agent_corrections_tenant_id   ON agent_corrections(tenant_id);
CREATE INDEX idx_agent_corrections_suggestion  ON agent_corrections(agent_suggestion_id);
CREATE INDEX idx_agent_corrections_agent       ON agent_corrections(tenant_id, agent_name, action_type);

-- ---------------------------------------------------------------------------
-- agent_autonomy_settings
-- Per-tenant, per-(agent, action_type) autonomy level.
-- Level 1 = notify only, 2 = suggest (HITL required), 3 = auto-apply if confident.
-- ---------------------------------------------------------------------------
CREATE TABLE agent_autonomy_settings (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_name              TEXT NOT NULL,
    action_type             TEXT NOT NULL,
    -- 1 = notify, 2 = suggest (HITL), 3 = auto-apply
    level                   SMALLINT NOT NULL DEFAULT 2,
    confidence_threshold    NUMERIC(3,2) NOT NULL DEFAULT 0.90,
    -- Set to TRUE by admin to block autonomy promoter from suggesting L3 for 90 days
    locked_at_l2            BOOLEAN NOT NULL DEFAULT FALSE,
    promoted_at             TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, agent_name, action_type),
    CONSTRAINT ck_autonomy_level CHECK (level BETWEEN 1 AND 3),
    CONSTRAINT ck_autonomy_confidence CHECK (confidence_threshold BETWEEN 0 AND 1)
);

ALTER TABLE agent_autonomy_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON agent_autonomy_settings
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON agent_autonomy_settings
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_autonomy_settings_tenant_id ON agent_autonomy_settings(tenant_id);
CREATE INDEX idx_autonomy_settings_agent     ON agent_autonomy_settings(tenant_id, agent_name);

COMMIT;
