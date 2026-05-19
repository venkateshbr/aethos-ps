-- =============================================================================
-- Migration 0003: General Ledger — journal_entries, journal_lines
-- =============================================================================
-- * journal_entries carry the header (entry_date, type, posting state).
-- * journal_lines carry the debit/credit detail with base-currency conversion.
-- * A trigger prevents any UPDATE on a posted journal_entry (immutability rule).
-- * Money: all amounts NUMERIC(15,2); fx_rate NUMERIC(15,6).
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
CREATE TYPE journal_entry_type AS ENUM ('standard', 'reversing', 'auto');
CREATE TYPE journal_line_direction AS ENUM ('DR', 'CR');

-- ---------------------------------------------------------------------------
-- Sequences
-- ---------------------------------------------------------------------------
-- Entry numbers are PER TENANT via a shared sequence; the service layer
-- formats them as "JE-{tenant_slug}-{seq}" or similar.
-- One global sequence is fine for v1; per-tenant sequences added in v1.1 if needed.
CREATE SEQUENCE journal_entry_number_seq START 1;

-- ---------------------------------------------------------------------------
-- journal_entries
-- ---------------------------------------------------------------------------
CREATE TABLE journal_entries (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    entry_number        TEXT NOT NULL,
    entry_type          journal_entry_type NOT NULL DEFAULT 'standard',
    -- Reversals: original_entry_id points to the entry being reversed
    original_entry_id   UUID REFERENCES journal_entries(id),
    description         TEXT,
    entry_date          DATE NOT NULL,
    -- Accounting period, e.g. "2026-05"
    period              TEXT NOT NULL,
    -- Source reference (invoice, payment, expense, manual…)
    reference_type      TEXT,
    reference_id        UUID,
    -- Posting state — posted_at IS NULL means draft
    posted_at           TIMESTAMPTZ,
    created_by          UUID NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- Note: no deleted_at — journal entries are immutable once posted;
    --       drafts can be voided via reversal.
);

ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON journal_entries
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON journal_entries
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_je_tenant_id      ON journal_entries(tenant_id);
CREATE INDEX idx_je_period         ON journal_entries(tenant_id, period);
CREATE INDEX idx_je_reference      ON journal_entries(tenant_id, reference_type, reference_id);
CREATE INDEX idx_je_entry_date     ON journal_entries(tenant_id, entry_date);

-- ---------------------------------------------------------------------------
-- Trigger: prevent UPDATE on posted journal_entries (GAAP immutability)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_prevent_posted_journal_edit()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.posted_at IS NOT NULL THEN
        RAISE EXCEPTION
            'Cannot modify posted journal entry %. Use a reversing entry instead.',
            OLD.id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prevent_posted_journal_edit
    BEFORE UPDATE ON journal_entries
    FOR EACH ROW EXECUTE FUNCTION trg_prevent_posted_journal_edit();

-- ---------------------------------------------------------------------------
-- journal_lines
-- ---------------------------------------------------------------------------
CREATE TABLE journal_lines (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_entry_id    UUID NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    direction           journal_line_direction NOT NULL,
    account_id          UUID NOT NULL REFERENCES accounts(id),
    -- Foreign-currency amount (e.g. GBP)
    amount              NUMERIC(15,2) NOT NULL,
    currency            CHAR(3) NOT NULL,
    -- Base-currency equivalent (tenant's base_currency, FX-converted)
    base_amount         NUMERIC(15,2) NOT NULL,
    -- Optional link to the FX rate row used for conversion
    fx_rate_id          UUID,
    description         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- No updated_at — lines are append-only; corrections via new reversing entry
);

ALTER TABLE journal_lines ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON journal_lines
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE INDEX idx_jl_journal_entry_id   ON journal_lines(journal_entry_id);
CREATE INDEX idx_jl_tenant_id          ON journal_lines(tenant_id);
CREATE INDEX idx_jl_account_id         ON journal_lines(tenant_id, account_id);

-- ---------------------------------------------------------------------------
-- period_locks
-- ---------------------------------------------------------------------------
CREATE TABLE period_locks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    period          TEXT NOT NULL,           -- "YYYY-MM"
    locked_by       UUID NOT NULL,
    locked_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, period)
);

ALTER TABLE period_locks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON period_locks
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE INDEX idx_period_locks_tenant_id ON period_locks(tenant_id);

COMMIT;
