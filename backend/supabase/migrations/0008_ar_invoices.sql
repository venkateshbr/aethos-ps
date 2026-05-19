-- =============================================================================
-- Migration 0008: AR Sub-Ledger — Invoices, Invoice Lines, Invoice Numbering
-- =============================================================================
-- Accounts-Receivable tables:
--   * invoice_status enum
--   * invoices          — AR document, Stripe Payment Link, public token
--   * invoice_lines     — per-line amounts, tax, optional time/expense linkage
--   * trg_invoice_number_seq trigger — atomic per-tenant sequence on INSERT
--
-- Money: NUMERIC(15,2). Timestamps: TIMESTAMPTZ.
-- RLS on all tenant-scoped tables.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Enum
-- ---------------------------------------------------------------------------
CREATE TYPE invoice_status AS ENUM (
    'draft',
    'approved',
    'sent',
    'paid',
    'voided',
    'overdue'
);

-- ---------------------------------------------------------------------------
-- invoices
-- Core AR document.  invoice_number is set by the trigger below.
-- public_token is a random URL-safe token used for the customer-facing
-- payment page (/pay/<token>) — regenerated on each send.
-- ---------------------------------------------------------------------------
CREATE TABLE invoices (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    engagement_id               UUID NOT NULL REFERENCES engagements(id) ON DELETE RESTRICT,
    client_id                   UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    -- Set by trg_invoice_number_seq on INSERT; placeholder overwritten immediately
    invoice_number              TEXT NOT NULL DEFAULT '',
    currency                    CHAR(3) NOT NULL DEFAULT 'USD',
    subtotal                    NUMERIC(15,2) NOT NULL DEFAULT 0,
    tax_total                   NUMERIC(15,2) NOT NULL DEFAULT 0,
    total                       NUMERIC(15,2) NOT NULL DEFAULT 0,
    status                      invoice_status NOT NULL DEFAULT 'draft',
    issue_date                  DATE,
    due_date                    DATE,
    paid_at                     TIMESTAMPTZ,
    -- Stripe integration
    stripe_payment_link_id      TEXT,
    stripe_payment_link_url     TEXT,
    -- Public-facing URL token (rotated on each send)
    public_token                TEXT UNIQUE DEFAULT encode(gen_random_bytes(24), 'base64url'),
    sent_at                     TIMESTAMPTZ,
    notes                       TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at                  TIMESTAMPTZ,
    UNIQUE (tenant_id, invoice_number),
    CONSTRAINT ck_invoices_subtotal_pos CHECK (subtotal >= 0),
    CONSTRAINT ck_invoices_tax_total_pos CHECK (tax_total >= 0),
    CONSTRAINT ck_invoices_total_pos    CHECK (total >= 0),
    CONSTRAINT ck_invoices_dates        CHECK (due_date IS NULL OR issue_date IS NULL OR due_date >= issue_date)
);

ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON invoices
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON invoices
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_invoices_tenant_status ON invoices(tenant_id, status)    WHERE deleted_at IS NULL;
CREATE INDEX idx_invoices_tenant_client ON invoices(tenant_id, client_id) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- invoice_lines
-- Each line on an invoice.  May reference a time_entry or project_expense
-- (nullable UUIDs; no FK to keep the data model flexible across billing models).
-- ---------------------------------------------------------------------------
CREATE TABLE invoice_lines (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_id      UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    description     TEXT NOT NULL,
    quantity        NUMERIC(10,2) NOT NULL DEFAULT 1,
    unit_price      NUMERIC(15,2) NOT NULL,
    amount          NUMERIC(15,2) NOT NULL,
    -- Tax linkage (optional; agent may suggest the correct rate)
    tax_rate_id     UUID REFERENCES tax_rates(id) ON DELETE SET NULL,
    tax_amount      NUMERIC(15,2) NOT NULL DEFAULT 0,
    -- Source linkage (nullable — adhoc lines have neither)
    time_entry_id   UUID,
    expense_id      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_il_quantity_pos    CHECK (quantity > 0),
    CONSTRAINT ck_il_unit_price_pos  CHECK (unit_price >= 0),
    CONSTRAINT ck_il_amount_pos      CHECK (amount >= 0),
    CONSTRAINT ck_il_tax_amount_pos  CHECK (tax_amount >= 0)
);

ALTER TABLE invoice_lines ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON invoice_lines
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE INDEX idx_invoice_lines_invoice_id ON invoice_lines(invoice_id);
CREATE INDEX idx_invoice_lines_tenant_id  ON invoice_lines(tenant_id);

-- ---------------------------------------------------------------------------
-- Invoice number sequence trigger
--
-- On INSERT into invoices:
--   1. Ensure invoice_number_sequences row exists for this tenant
--      (INSERT … ON CONFLICT DO NOTHING — idempotent).
--   2. Atomically increment last_number and read back the new value.
--   3. Format as 'INV-0001', 'INV-0042', etc. (zero-padded to 4 digits,
--      grows beyond 4 digits naturally once past 9999).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_next_invoice_number(p_tenant_id UUID)
RETURNS TEXT LANGUAGE plpgsql AS $$
DECLARE
    v_next INTEGER;
BEGIN
    -- Ensure sequence row exists
    INSERT INTO invoice_number_sequences (tenant_id, last_number)
    VALUES (p_tenant_id, 0)
    ON CONFLICT (tenant_id) DO NOTHING;

    -- Atomic increment + read
    UPDATE invoice_number_sequences
       SET last_number = last_number + 1
     WHERE tenant_id = p_tenant_id
    RETURNING last_number INTO v_next;

    RETURN 'INV-' || LPAD(v_next::TEXT, 4, '0');
END;
$$;

CREATE OR REPLACE FUNCTION trg_fn_invoice_number_seq()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- Only generate when the number has not already been supplied
    -- (allows manual override during data migrations / tests).
    IF NEW.invoice_number IS NULL OR NEW.invoice_number = '' THEN
        NEW.invoice_number := fn_next_invoice_number(NEW.tenant_id);
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_invoice_number_seq
    BEFORE INSERT ON invoices
    FOR EACH ROW EXECUTE FUNCTION trg_fn_invoice_number_seq();

COMMIT;
