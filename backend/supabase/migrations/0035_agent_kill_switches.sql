-- Agent kill switches and circuit breaker state.
--
-- Reuses agent_autonomy_settings so autonomy level, admin enablement, and
-- operational circuit state stay on the same tenant/agent/action control row.

BEGIN;

ALTER TABLE agent_autonomy_settings
    ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS failure_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS failure_threshold INTEGER NOT NULL DEFAULT 3,
    ADD COLUMN IF NOT EXISTS last_failure_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS circuit_opened_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS circuit_open_until TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS circuit_open_reason TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_agent_autonomy_failure_count'
    ) THEN
        ALTER TABLE agent_autonomy_settings
            ADD CONSTRAINT ck_agent_autonomy_failure_count
            CHECK (failure_count >= 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_agent_autonomy_failure_threshold'
    ) THEN
        ALTER TABLE agent_autonomy_settings
            ADD CONSTRAINT ck_agent_autonomy_failure_threshold
            CHECK (failure_threshold BETWEEN 1 AND 25);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_autonomy_settings_open_circuit
    ON agent_autonomy_settings (tenant_id, agent_name, action_type, circuit_open_until)
    WHERE circuit_open_until IS NOT NULL;

COMMENT ON COLUMN agent_autonomy_settings.is_enabled IS
    'Admin kill switch. FALSE blocks this agent/action before role or autonomy evaluation.';
COMMENT ON COLUMN agent_autonomy_settings.failure_count IS
    'Consecutive failed tool/action executions observed by the agent run ledger.';
COMMENT ON COLUMN agent_autonomy_settings.failure_threshold IS
    'Consecutive failures required before opening the circuit for this agent/action.';
COMMENT ON COLUMN agent_autonomy_settings.circuit_open_until IS
    'When set in the future, policy denies this agent/action until the circuit cools down or is reset.';

COMMIT;
