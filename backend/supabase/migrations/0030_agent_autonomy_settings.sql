-- ---------------------------------------------------------------------------
-- Migration 0030: Agent Autonomy Settings — UI-managed level rows
--
-- The agent_autonomy_settings table was created in migration 0005.
-- This migration documents and supports the UI/API convention:
--
--   action_type = 'default'
--       A synthetic row used by the Autonomy Settings UI (POST /agents/{name}/set-level)
--       to record a per-agent level that is NOT tied to a specific action_type.
--       The autonomy_promoter worker uses real action_type values (e.g. 'draft_invoice');
--       the UI uses 'default' so operator overrides do not conflict with promoter rows.
--
-- The UNIQUE constraint on (tenant_id, agent_name, action_type) from migration 0005
-- already handles upsert safety for 'default' rows — no schema changes needed.
--
-- This migration adds:
--   1. A comment on the table to document the 'default' action_type convention.
--   2. A partial index to speed up the common UI lookup
--      (SELECT level WHERE action_type = 'default').
-- ---------------------------------------------------------------------------

COMMENT ON TABLE agent_autonomy_settings IS
    'Per-tenant, per-(agent, action_type) autonomy level. '
    'action_type=''default'' rows are set by the Autonomy Settings UI; '
    'other action_type rows are managed by the autonomy_promoter worker.';

-- Partial index for the UI read path
CREATE INDEX IF NOT EXISTS idx_autonomy_settings_default_action
    ON agent_autonomy_settings (tenant_id, agent_name)
    WHERE action_type = 'default';
