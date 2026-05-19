-- =============================================================================
-- Migration 0002: Chart of Accounts (accounts table + COA seed trigger)
-- =============================================================================
-- Creates accounts table.  A trigger on tenants fires after INSERT and seeds
-- the standard 12-account COA for every new workspace.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Enum
-- ---------------------------------------------------------------------------
CREATE TYPE account_type AS ENUM ('asset', 'liability', 'equity', 'revenue', 'expense');

-- ---------------------------------------------------------------------------
-- accounts
-- ---------------------------------------------------------------------------
CREATE TABLE accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code            TEXT NOT NULL,
    name            TEXT NOT NULL,
    account_type    account_type NOT NULL,
    is_system       BOOLEAN NOT NULL DEFAULT FALSE,
    -- Self-referencing parent for sub-accounts
    parent_id       UUID REFERENCES accounts(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    UNIQUE (tenant_id, code)
);

ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON accounts
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_accounts_tenant_id   ON accounts(tenant_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_accounts_code        ON accounts(tenant_id, code) WHERE deleted_at IS NULL;
CREATE INDEX idx_accounts_type        ON accounts(tenant_id, account_type) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- COA seed function
-- Standard 12-account chart seeded for every new tenant.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION seed_standard_coa(p_tenant_id UUID)
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO accounts (tenant_id, code, name, account_type, is_system)
    VALUES
        -- Assets
        (p_tenant_id, '1100', 'Bank',                       'asset',     TRUE),
        (p_tenant_id, '1200', 'Accounts Receivable',        'asset',     TRUE),
        (p_tenant_id, '1300', 'Input Tax Recoverable',      'asset',     TRUE),
        (p_tenant_id, '1500', 'Prepaid Expenses',           'asset',     TRUE),
        -- Liabilities
        (p_tenant_id, '2000', 'Accounts Payable',           'liability', TRUE),
        (p_tenant_id, '2100', 'Accrued Reimbursement',      'liability', TRUE),
        (p_tenant_id, '2300', 'Sales Tax Payable',          'liability', TRUE),
        -- Equity
        (p_tenant_id, '3000', 'Retained Earnings',          'equity',    TRUE),
        -- Revenue
        (p_tenant_id, '4000', 'Revenue',                    'revenue',   TRUE),
        -- Expenses
        (p_tenant_id, '5000', 'Expenses',                   'expense',   TRUE),
        (p_tenant_id, '5100', 'Employee Expenses',          'expense',   TRUE),
        -- FX
        (p_tenant_id, '7900', 'Realized FX Gain/Loss',     'expense',   TRUE)
    ON CONFLICT (tenant_id, code) DO NOTHING;
END;
$$;

-- ---------------------------------------------------------------------------
-- Trigger: seed COA when a new tenant is created
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_seed_coa_on_tenant_insert()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    PERFORM seed_standard_coa(NEW.id);
    RETURN NEW;
END;
$$;

CREATE TRIGGER seed_coa_after_tenant_insert
    AFTER INSERT ON tenants
    FOR EACH ROW EXECUTE FUNCTION trg_seed_coa_on_tenant_insert();

COMMIT;
