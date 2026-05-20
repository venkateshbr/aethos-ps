-- =============================================================================
-- Migration 0013: Bill Payment Batches — NACHA/CSV export support
-- =============================================================================
-- Tables:
--   * bill_payment_batches — a grouping of bills to pay in one bank run
--   * bill_payment_items   — individual bill→batch line items
--
-- Money: NUMERIC(15,2). Timestamps: TIMESTAMPTZ.
-- RLS on all tenant-scoped tables.
-- =============================================================================

BEGIN;

CREATE TYPE batch_status AS ENUM ('draft', 'approved', 'sent_to_bank', 'cancelled');

CREATE TABLE bill_payment_batches (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    status              batch_status NOT NULL DEFAULT 'draft',
    total               NUMERIC(15,2) NOT NULL DEFAULT 0,
    currency            CHAR(3) NOT NULL DEFAULT 'USD',
    bank_account_label  TEXT,
    pay_date            DATE,
    file_format         TEXT,              -- 'nacha' | 'csv'
    exported_at         TIMESTAMPTZ,
    created_by          UUID NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE bill_payment_batches ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON bill_payment_batches
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON bill_payment_batches
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE TABLE bill_payment_items (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id    UUID NOT NULL REFERENCES bill_payment_batches(id) ON DELETE CASCADE,
    tenant_id   UUID NOT NULL REFERENCES tenants(id),
    bill_id     UUID NOT NULL REFERENCES bills(id),
    amount      NUMERIC(15,2) NOT NULL,
    currency    CHAR(3) NOT NULL DEFAULT 'USD',
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE bill_payment_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON bill_payment_items
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);
CREATE INDEX idx_bpi_batch ON bill_payment_items(batch_id);
CREATE INDEX idx_bpi_bill  ON bill_payment_items(bill_id);

COMMIT;
