-- =============================================================================
-- Migration 0081: Invoice Public Token Revocations
-- =============================================================================
-- Keeps retired public invoice tokens distinguishable from unknown tokens.
-- Public invoice lookups return 410 Gone for revoked tokens, which lets
-- customer-facing payment pages handle mid-payment token rotation explicitly.
-- =============================================================================

BEGIN;

CREATE TABLE invoice_public_token_revocations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_id      UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    public_token    TEXT NOT NULL UNIQUE,
    revoked_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_by      UUID,
    reason          TEXT NOT NULL DEFAULT 'rotated'
);

ALTER TABLE invoice_public_token_revocations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON invoice_public_token_revocations
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE INDEX idx_invoice_public_token_revocations_invoice
    ON invoice_public_token_revocations(tenant_id, invoice_id, revoked_at DESC);

COMMIT;
