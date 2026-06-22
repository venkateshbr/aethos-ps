-- Human corrections become durable eval-case candidates.
--
-- The candidate row indexes a correction for review/export without duplicating
-- the full input/output payloads already stored on agent_suggestions and
-- agent_corrections.

BEGIN;

CREATE TYPE agent_eval_candidate_status AS ENUM (
    'candidate',
    'accepted',
    'dismissed',
    'exported'
);

CREATE TABLE agent_eval_candidates (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_correction_id     UUID NOT NULL REFERENCES agent_corrections(id) ON DELETE CASCADE,
    agent_suggestion_id     UUID NOT NULL REFERENCES agent_suggestions(id) ON DELETE CASCADE,
    agent_name              TEXT NOT NULL,
    action_type             TEXT NOT NULL,
    eval_case_key           TEXT NOT NULL,
    status                  agent_eval_candidate_status NOT NULL DEFAULT 'candidate',
    input_hash              TEXT,
    original_output_hash    TEXT,
    corrected_output_hash   TEXT,
    reason                  TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, agent_correction_id),
    UNIQUE (tenant_id, eval_case_key)
);

ALTER TABLE agent_eval_candidates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON agent_eval_candidates
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON agent_eval_candidates
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_agent_eval_candidates_status
    ON agent_eval_candidates(tenant_id, status, created_at DESC);
CREATE INDEX idx_agent_eval_candidates_agent
    ON agent_eval_candidates(tenant_id, agent_name, action_type, created_at DESC);
CREATE INDEX idx_agent_eval_candidates_suggestion
    ON agent_eval_candidates(agent_suggestion_id);

COMMIT;
