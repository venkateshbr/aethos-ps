-- Explicit gates for L3 autonomy promotion.

BEGIN;

ALTER TABLE agent_autonomy_settings
    ADD COLUMN IF NOT EXISTS l3_opt_in BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS eval_passed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS eval_score NUMERIC(5,4),
    ADD COLUMN IF NOT EXISTS max_auto_risk agent_tool_risk_class NOT NULL DEFAULT 'draft';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_agent_autonomy_eval_score'
    ) THEN
        ALTER TABLE agent_autonomy_settings
            ADD CONSTRAINT ck_agent_autonomy_eval_score
            CHECK (eval_score IS NULL OR eval_score BETWEEN 0 AND 1);
    END IF;
END $$;

COMMENT ON COLUMN agent_autonomy_settings.l3_opt_in IS
    'Explicit admin opt-in required before this agent/action can be promoted to L3.';
COMMENT ON COLUMN agent_autonomy_settings.eval_passed_at IS
    'Timestamp of the latest passing eval gate for this agent/action.';
COMMENT ON COLUMN agent_autonomy_settings.max_auto_risk IS
    'Highest tool/action risk class this agent/action may execute automatically at L3.';

COMMIT;
