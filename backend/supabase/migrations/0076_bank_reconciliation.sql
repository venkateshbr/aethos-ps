-- =============================================================================
-- Migration 0076: Bank Reconciliation And Suspense Close Evidence
-- =============================================================================
-- Adds durable imported bank transaction rows plus journal-entry match evidence
-- so month-end close can block on unmatched cash movements. Also seeds a
-- standard Suspense account for items that need finance review before close.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Suspense account seed for existing and future tenants
-- ---------------------------------------------------------------------------
INSERT INTO accounts (tenant_id, code, name, account_type, is_system)
SELECT id, '1999', 'Suspense', 'asset', TRUE
FROM tenants
ON CONFLICT (tenant_id, code) DO NOTHING;

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
        (p_tenant_id, '1999', 'Suspense',                   'asset',     TRUE),
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
        (p_tenant_id, '7900', 'Realized FX Gain/Loss',      'expense',   TRUE)
    ON CONFLICT (tenant_id, code) DO NOTHING;
END;
$$;

-- ---------------------------------------------------------------------------
-- bank_transactions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bank_transactions (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    account_id                  UUID REFERENCES accounts(id),
    external_account_id          TEXT,
    external_transaction_id      TEXT,
    transaction_date             DATE NOT NULL,
    posted_at                   TIMESTAMPTZ,
    description                 TEXT,
    counterparty_name            TEXT,
    amount                      NUMERIC(15,2) NOT NULL,
    currency                    CHAR(3) NOT NULL,
    base_amount                 NUMERIC(15,2),
    status                      TEXT NOT NULL DEFAULT 'unmatched',
    matched_journal_entry_id     UUID REFERENCES journal_entries(id),
    match_confidence             NUMERIC(5,4),
    match_evidence               JSONB NOT NULL DEFAULT '{}'::jsonb,
    imported_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at                  TIMESTAMPTZ,
    CONSTRAINT ck_bank_transactions_status CHECK (
        status IN ('unmatched', 'needs_review', 'matched', 'ignored')
    ),
    CONSTRAINT ck_bank_transactions_confidence CHECK (
        match_confidence IS NULL OR (match_confidence >= 0 AND match_confidence <= 1)
    ),
    CONSTRAINT uq_bank_transactions_external UNIQUE (
        tenant_id, external_account_id, external_transaction_id
    )
);

ALTER TABLE bank_transactions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "tenant_isolation" ON bank_transactions;
CREATE POLICY "tenant_isolation" ON bank_transactions
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

DROP POLICY IF EXISTS "authenticated_member_read" ON bank_transactions;
CREATE POLICY "authenticated_member_read" ON bank_transactions
    FOR SELECT
    TO authenticated
    USING (app.is_tenant_member(tenant_id));

CREATE TRIGGER set_updated_at BEFORE UPDATE ON bank_transactions
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX IF NOT EXISTS idx_bank_transactions_period
    ON bank_transactions(tenant_id, transaction_date)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_bank_transactions_status
    ON bank_transactions(tenant_id, status, transaction_date)
    WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- bank_reconciliation_matches
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bank_reconciliation_matches (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    bank_transaction_id       UUID NOT NULL REFERENCES bank_transactions(id) ON DELETE CASCADE,
    journal_entry_id          UUID NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    status                   TEXT NOT NULL DEFAULT 'matched',
    matched_by               TEXT,
    match_evidence            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at               TIMESTAMPTZ,
    CONSTRAINT ck_bank_reconciliation_matches_status CHECK (
        status IN ('matched', 'rejected', 'voided')
    ),
    UNIQUE (tenant_id, bank_transaction_id, journal_entry_id)
);

ALTER TABLE bank_reconciliation_matches ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "tenant_isolation" ON bank_reconciliation_matches;
CREATE POLICY "tenant_isolation" ON bank_reconciliation_matches
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

DROP POLICY IF EXISTS "authenticated_member_read" ON bank_reconciliation_matches;
CREATE POLICY "authenticated_member_read" ON bank_reconciliation_matches
    FOR SELECT
    TO authenticated
    USING (app.is_tenant_member(tenant_id));

CREATE TRIGGER set_updated_at BEFORE UPDATE ON bank_reconciliation_matches
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX IF NOT EXISTS idx_bank_reconciliation_matches_transaction
    ON bank_reconciliation_matches(tenant_id, bank_transaction_id)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_bank_reconciliation_matches_journal
    ON bank_reconciliation_matches(tenant_id, journal_entry_id)
    WHERE deleted_at IS NULL;

COMMIT;
