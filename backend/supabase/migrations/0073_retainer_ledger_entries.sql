-- =============================================================================
-- Migration 0073: Retainer Ledger Entries
--
-- Tracks retainer deposits and drawdowns per engagement. Invoice drafting uses
-- this ledger to cap retainer draw offsets by actual available balance.
-- =============================================================================

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'retainer_ledger_entry_type') THEN
        CREATE TYPE retainer_ledger_entry_type AS ENUM (
            'deposit',
            'draw',
            'credit_adjustment',
            'debit_adjustment'
        );
    END IF;
END $$;

CREATE TABLE retainer_ledger_entries (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    engagement_id       UUID NOT NULL REFERENCES engagements(id) ON DELETE CASCADE,
    invoice_id          UUID REFERENCES invoices(id) ON DELETE SET NULL,
    entry_type          retainer_ledger_entry_type NOT NULL,
    amount              NUMERIC(15,2) NOT NULL,
    currency            CHAR(3) NOT NULL DEFAULT 'USD',
    description         TEXT,
    entry_date          DATE NOT NULL DEFAULT CURRENT_DATE,
    created_by_agent    TEXT,
    created_by_user_id  UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,
    CONSTRAINT ck_retainer_ledger_amount_pos CHECK (amount >= 0)
);

ALTER TABLE retainer_ledger_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_isolation" ON retainer_ledger_entries
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY "authenticated_member_read" ON retainer_ledger_entries
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE TRIGGER set_updated_at BEFORE UPDATE ON retainer_ledger_entries
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE UNIQUE INDEX uq_retainer_ledger_draw_invoice
    ON retainer_ledger_entries (tenant_id, engagement_id, invoice_id)
    WHERE entry_type = 'draw'
      AND invoice_id IS NOT NULL
      AND deleted_at IS NULL;

CREATE INDEX idx_retainer_ledger_engagement
    ON retainer_ledger_entries (tenant_id, engagement_id, entry_date)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_retainer_ledger_invoice
    ON retainer_ledger_entries (tenant_id, invoice_id)
    WHERE invoice_id IS NOT NULL AND deleted_at IS NULL;

COMMENT ON TABLE retainer_ledger_entries IS
    'Per-engagement retainer deposits, drawdowns, and adjustments used to derive available retainer balance.';

COMMIT;
