BEGIN;

ALTER TABLE tenant_approval_policies
    ADD COLUMN IF NOT EXISTS manual_journal_approval_threshold NUMERIC(18, 2)
    NOT NULL DEFAULT 10000.00;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_tenant_approval_policy_manual_journal_threshold'
    ) THEN
        ALTER TABLE tenant_approval_policies
            ADD CONSTRAINT ck_tenant_approval_policy_manual_journal_threshold
            CHECK (manual_journal_approval_threshold >= 0);
    END IF;
END $$;

COMMENT ON COLUMN tenant_approval_policies.manual_journal_approval_threshold IS
    'Manual journal total debit amount at or above this value routes to Inbox approval.';

COMMIT;
