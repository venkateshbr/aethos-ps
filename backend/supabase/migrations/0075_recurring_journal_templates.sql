-- =============================================================================
-- Migration 0075: Recurring Journal Templates
-- =============================================================================
-- Month-end recurring journals are stored as tenant-owned templates. The close
-- workflow turns active templates into HITL draft-journal suggestions; posting
-- still flows through the existing inbox/manual-journal path.
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS recurring_journal_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    description     TEXT,
    schedule_day    INTEGER NOT NULL DEFAULT 31,
    start_period    TEXT NOT NULL,
    end_period      TEXT,
    currency        CHAR(3) NOT NULL DEFAULT 'USD',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    CONSTRAINT ck_rjt_schedule_day CHECK (schedule_day BETWEEN 1 AND 31),
    CONSTRAINT ck_rjt_start_period CHECK (start_period ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    CONSTRAINT ck_rjt_end_period CHECK (
        end_period IS NULL OR end_period ~ '^\d{4}-(0[1-9]|1[0-2])$'
    ),
    CONSTRAINT ck_rjt_period_order CHECK (end_period IS NULL OR end_period >= start_period),
    CONSTRAINT ck_rjt_currency CHECK (currency ~ '^[A-Z]{3}$')
);

CREATE TABLE IF NOT EXISTS recurring_journal_template_lines (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    template_id     UUID NOT NULL REFERENCES recurring_journal_templates(id) ON DELETE CASCADE,
    account_id      UUID NOT NULL REFERENCES accounts(id),
    direction       journal_line_direction NOT NULL,
    amount          NUMERIC(15,2) NOT NULL,
    description     TEXT,
    order_index     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_rjtl_amount_positive CHECK (amount > 0)
);

ALTER TABLE recurring_journal_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE recurring_journal_template_lines ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "tenant_isolation" ON recurring_journal_templates;
CREATE POLICY "tenant_isolation" ON recurring_journal_templates
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

DROP POLICY IF EXISTS "authenticated_member_read" ON recurring_journal_templates;
CREATE POLICY "authenticated_member_read" ON recurring_journal_templates
    FOR SELECT
    TO authenticated
    USING (app.is_tenant_member(tenant_id));

DROP POLICY IF EXISTS "tenant_isolation" ON recurring_journal_template_lines;
CREATE POLICY "tenant_isolation" ON recurring_journal_template_lines
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

DROP POLICY IF EXISTS "authenticated_member_read" ON recurring_journal_template_lines;
CREATE POLICY "authenticated_member_read" ON recurring_journal_template_lines
    FOR SELECT
    TO authenticated
    USING (app.is_tenant_member(tenant_id));

CREATE TRIGGER set_updated_at BEFORE UPDATE ON recurring_journal_templates
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE UNIQUE INDEX IF NOT EXISTS idx_rjt_tenant_name_active
    ON recurring_journal_templates(tenant_id, lower(name))
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_rjt_tenant_active_period
    ON recurring_journal_templates(tenant_id, is_active, start_period, end_period)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_rjtl_template
    ON recurring_journal_template_lines(template_id, order_index);

COMMIT;
