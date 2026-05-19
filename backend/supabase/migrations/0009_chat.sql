-- =============================================================================
-- Migration 0009: Chat Threads and Messages
-- =============================================================================
-- Persists the copilot conversation history:
--   * chat_threads  — one conversation session per user / tenant
--   * chat_messages — ordered message log with full LLM metadata
--
-- Supports all PydanticAI message roles: user, assistant, tool, system.
-- Tool call inputs and outputs stored as JSONB for agent replay / Langfuse
-- cross-reference.
--
-- Timestamps: TIMESTAMPTZ. RLS on both tables.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- chat_threads
-- One thread = one conversation session.
-- user_id references auth.users (Supabase Auth) — no cross-schema FK constraint.
-- ---------------------------------------------------------------------------
CREATE TABLE chat_threads (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    -- Supabase Auth user who owns this thread
    user_id     UUID NOT NULL,
    title       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ
);

ALTER TABLE chat_threads ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON chat_threads
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON chat_threads
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_chat_threads_tenant_id ON chat_threads(tenant_id)          WHERE deleted_at IS NULL;
CREATE INDEX idx_chat_threads_user_id   ON chat_threads(tenant_id, user_id) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- chat_messages
-- Append-only message log.  No updated_at — messages are immutable once written.
-- Roles: user | assistant | tool | system  (matches PydanticAI message roles).
-- Tool messages carry tool_name, tool_input, tool_output for agent replay.
-- LLM metadata (model, token usage, finish_reason) recorded on assistant turns.
-- ---------------------------------------------------------------------------
CREATE TABLE chat_messages (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id               UUID NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    -- Message role
    role                    TEXT NOT NULL,
    -- Text content (may be NULL for pure tool calls)
    content                 TEXT,
    -- Tool metadata (populated when role = 'tool')
    tool_name               TEXT,
    tool_input              JSONB,
    tool_output             JSONB,
    -- LLM response metadata (populated when role = 'assistant')
    finish_reason           TEXT,
    model                   TEXT,
    usage_input_tokens      INTEGER,
    usage_output_tokens     INTEGER,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_chat_messages_role CHECK (role IN ('user', 'assistant', 'tool', 'system')),
    CONSTRAINT ck_chat_messages_tokens_pos CHECK (
        (usage_input_tokens  IS NULL OR usage_input_tokens  >= 0) AND
        (usage_output_tokens IS NULL OR usage_output_tokens >= 0)
    )
);

ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON chat_messages
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

-- Primary access pattern: fetch messages for a thread ordered by time
CREATE INDEX idx_chat_messages_thread_time ON chat_messages(thread_id, created_at);
CREATE INDEX idx_chat_messages_tenant_id   ON chat_messages(tenant_id);

COMMIT;
