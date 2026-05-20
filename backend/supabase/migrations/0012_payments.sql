-- =============================================================================
-- Migration 0012: Payments — AR payment recording
-- =============================================================================
-- Tracks payments received against invoices (AR sub-ledger).
-- Linked to invoices and optionally to FX rates for multi-currency conversions.
-- Stripe payment intent / charge IDs stored for reconciliation.
--
-- Money: NUMERIC(15,2). Timestamps: TIMESTAMPTZ.
-- RLS on all tenant-scoped tables.
-- =============================================================================
-- Prahari review required — see docs/team/SECURITY_REVIEW.md

BEGIN;

CREATE TABLE IF NOT EXISTS payments (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_id                  UUID NOT NULL REFERENCES invoices(id) ON DELETE RESTRICT,
    amount                      NUMERIC(15,2) NOT NULL,
    currency                    CHAR(3) NOT NULL,
    base_amount                 NUMERIC(15,2) NOT NULL,
    fx_rate_id                  UUID REFERENCES fx_rates(id) ON DELETE SET NULL,
    stripe_payment_intent_id    TEXT UNIQUE,
    stripe_charge_id            TEXT,
    paid_at                     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes                       TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_payments_amount_pos       CHECK (amount > 0),
    CONSTRAINT ck_payments_base_amount_pos  CHECK (base_amount > 0)
);

ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON payments
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE INDEX IF NOT EXISTS idx_payments_invoice  ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_payments_tenant   ON payments(tenant_id, paid_at);
CREATE INDEX IF NOT EXISTS idx_payments_intent   ON payments(stripe_payment_intent_id)
    WHERE stripe_payment_intent_id IS NOT NULL;

COMMIT;
