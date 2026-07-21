-- =============================================================================
-- Migration 0105: Nous tool sessions (server-resolved context tokens)
--
-- The Hermes/Nous MCP tools require a per-turn context that the broker verifies
-- (tenant/user/thread/scope). Previously the API embedded a ~360-char signed
-- `context_ref` in the model prompt and asked the model to copy it verbatim into
-- every tool call. Weaker models mangled that long opaque string, so the broker
-- rejected the tool call with HTTP 400 (see docs/architecture/nous-hermes-agentic-assessment.md).
--
-- This table lets the API instead hand the model a SHORT opaque token
-- (`cts_...`, ~26 chars) that the broker resolves server-side to the full
-- context. Short tokens survive model copy reliably. Rows are short-lived and
-- resolved with the service role only; the broker checks expiry + scope.
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS atlas_tool_sessions (
    token       TEXT PRIMARY KEY,
    tenant_id   UUID        NOT NULL,
    user_id     UUID        NOT NULL,
    thread_id   TEXT        NOT NULL,
    scope       TEXT        NOT NULL,
    nonce       TEXT        NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Supports expiry-based pruning and lookups.
CREATE INDEX IF NOT EXISTS ix_atlas_tool_sessions_expires_at
    ON atlas_tool_sessions (expires_at);

-- Defense in depth: only the service role (broker + mint) touches this table.
-- No anon/authenticated policies are defined, so RLS denies all other roles.
ALTER TABLE atlas_tool_sessions ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE atlas_tool_sessions IS
    'Short-lived server-resolved context tokens for Nous/Hermes MCP tool calls. '
    'The model copies the short token; the broker resolves tenant/user/thread/scope here.';
COMMENT ON COLUMN atlas_tool_sessions.token IS
    'Opaque short token (cts_...) handed to the model and passed back as context_ref.';
COMMENT ON COLUMN atlas_tool_sessions.expires_at IS
    'Hard expiry; the broker rejects resolution after this instant.';

COMMIT;
