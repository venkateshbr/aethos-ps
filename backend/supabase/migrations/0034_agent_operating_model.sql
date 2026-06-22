-- =============================================================================
-- Migration 0034: Agent Operating Model Ledger
--
-- Adds the durable audit spine for agent runs, tool calls, long-running
-- workflow runs, and memory items.  Existing agent_suggestions + hitl_tasks
-- remain the HITL proposal/review substrate; these tables record execution
-- provenance around those proposals and direct tool calls.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
CREATE TYPE agent_run_status AS ENUM ('running', 'succeeded', 'failed', 'cancelled');

CREATE TYPE agent_tool_risk_class AS ENUM (
    'read_only',
    'draft',
    'write_low_risk',
    'write_money_in',
    'write_money_out',
    'accounting'
);

CREATE TYPE agent_tool_invocation_status AS ENUM (
    'running',
    'succeeded',
    'failed',
    'skipped'
);

CREATE TYPE agent_workflow_run_status AS ENUM (
    'running',
    'waiting_on_human',
    'succeeded',
    'failed',
    'cancelled'
);

-- ---------------------------------------------------------------------------
-- agent_runs
-- One row per agent execution attempt.  Payloads are represented by hashes so
-- traceability exists without duplicating full chat/document content here.
-- ---------------------------------------------------------------------------
CREATE TABLE agent_runs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_name              TEXT NOT NULL,
    trigger_type            TEXT NOT NULL DEFAULT 'manual',
    status                  agent_run_status NOT NULL DEFAULT 'running',
    user_id                 UUID,
    source_document_id      UUID REFERENCES documents(id),
    source_document_hash    TEXT,
    prompt_version          TEXT,
    model_version           TEXT,
    input_hash              TEXT,
    output_hash             TEXT,
    usage_input_tokens      INTEGER,
    usage_output_tokens     INTEGER,
    cost_usd                NUMERIC(12,6),
    trace_id                TEXT,
    replay_pointer          TEXT,
    error_message           TEXT,
    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_agent_runs_tokens_pos CHECK (
        (usage_input_tokens IS NULL OR usage_input_tokens >= 0)
        AND (usage_output_tokens IS NULL OR usage_output_tokens >= 0)
    ),
    CONSTRAINT ck_agent_runs_cost_pos CHECK (cost_usd IS NULL OR cost_usd >= 0)
);

ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON agent_runs
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON agent_runs
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_agent_runs_tenant_created
    ON agent_runs(tenant_id, created_at DESC);
CREATE INDEX idx_agent_runs_tenant_agent
    ON agent_runs(tenant_id, agent_name, created_at DESC);
CREATE INDEX idx_agent_runs_status
    ON agent_runs(tenant_id, status, created_at DESC);
CREATE INDEX idx_agent_runs_trace_id
    ON agent_runs(tenant_id, trace_id)
    WHERE trace_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- agent_tool_invocations
-- One row per tool call made during an agent run.
-- ---------------------------------------------------------------------------
CREATE TABLE agent_tool_invocations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_run_id            UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    tool_name               TEXT NOT NULL,
    risk_class              agent_tool_risk_class NOT NULL,
    status                  agent_tool_invocation_status NOT NULL DEFAULT 'succeeded',
    external_tool_call_id   TEXT,
    input_hash              TEXT,
    output_hash             TEXT,
    input_snapshot          JSONB NOT NULL DEFAULT '{}'::JSONB,
    output_snapshot         JSONB NOT NULL DEFAULT '{}'::JSONB,
    duration_ms             INTEGER,
    error_message           TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_agent_tool_duration_pos CHECK (
        duration_ms IS NULL OR duration_ms >= 0
    )
);

ALTER TABLE agent_tool_invocations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON agent_tool_invocations
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE INDEX idx_agent_tool_invocations_run
    ON agent_tool_invocations(agent_run_id, created_at);
CREATE INDEX idx_agent_tool_invocations_tenant_tool
    ON agent_tool_invocations(tenant_id, tool_name, created_at DESC);
CREATE INDEX idx_agent_tool_invocations_risk
    ON agent_tool_invocations(tenant_id, risk_class, created_at DESC);

-- ---------------------------------------------------------------------------
-- agent_workflow_runs
-- Durable container for long-running business goals.  No worker uses it yet;
-- Phase 3 workflow loops will attach deterministic steps behind this table.
-- ---------------------------------------------------------------------------
CREATE TABLE agent_workflow_runs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    workflow_name           TEXT NOT NULL,
    status                  agent_workflow_run_status NOT NULL DEFAULT 'running',
    owner_agent_name        TEXT,
    user_id                 UUID,
    current_step            TEXT,
    goal_snapshot           JSONB NOT NULL DEFAULT '{}'::JSONB,
    state_snapshot          JSONB NOT NULL DEFAULT '{}'::JSONB,
    trace_id                TEXT,
    replay_pointer          TEXT,
    error_message           TEXT,
    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE agent_workflow_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON agent_workflow_runs
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON agent_workflow_runs
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_agent_workflow_runs_tenant_created
    ON agent_workflow_runs(tenant_id, created_at DESC);
CREATE INDEX idx_agent_workflow_runs_status
    ON agent_workflow_runs(tenant_id, status, created_at DESC);

-- ---------------------------------------------------------------------------
-- agent_memory_items
-- Tenant-scoped durable memory candidates.  Human corrections and approved
-- preferences can be promoted here in later slices.
-- ---------------------------------------------------------------------------
CREATE TABLE agent_memory_items (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_name              TEXT,
    memory_type             TEXT NOT NULL,
    content_hash            TEXT NOT NULL,
    content_snapshot        JSONB NOT NULL DEFAULT '{}'::JSONB,
    source_type             TEXT,
    source_id               UUID,
    confidence              NUMERIC(3,2),
    expires_at              TIMESTAMPTZ,
    created_by_user_id      UUID,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_agent_memory_confidence CHECK (
        confidence IS NULL OR confidence BETWEEN 0 AND 1
    )
);

ALTER TABLE agent_memory_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON agent_memory_items
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON agent_memory_items
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_agent_memory_items_tenant_agent
    ON agent_memory_items(tenant_id, agent_name, memory_type, created_at DESC);
CREATE UNIQUE INDEX idx_agent_memory_items_content_hash
    ON agent_memory_items(tenant_id, memory_type, content_hash);

COMMIT;
