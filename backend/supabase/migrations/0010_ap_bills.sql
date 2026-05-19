-- =============================================================================
-- Migration 0010: AP Sub-Ledger — Bills, Bill Lines, Bill Numbering
-- =============================================================================
-- Accounts-Payable tables:
--   * bill_status enum
--   * bill_number_sequences   — per-tenant counter (mirrors invoice_number_sequences)
--   * bills                   — AP document from vendor
--   * bill_lines              — per-line amounts, tax, expense account linkage
--   * trg_bill_number_seq     — atomic per-tenant sequence on INSERT (BILL-0001…)
--
-- Money: NUMERIC(15,2). Timestamps: TIMESTAMPTZ.
-- RLS on all tenant-scoped tables.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Enum
-- ---------------------------------------------------------------------------
CREATE TYPE bill_status AS ENUM (
    'draft',
    'approved',
    'paid',
    'partially_paid',
    'voided',
    'cancelled'
);

-- ---------------------------------------------------------------------------
-- bill_number_sequences
-- Per-tenant monotonic counter.  Mirrors invoice_number_sequences pattern.
-- ---------------------------------------------------------------------------
CREATE TABLE bill_number_sequences (
    tenant_id   UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    last_number INTEGER NOT NULL DEFAULT 0
);

ALTER TABLE bill_number_sequences ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON bill_number_sequences
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

-- ---------------------------------------------------------------------------
-- bills
-- Core AP document.  bill_number set by trigger below.
-- client_id must reference a client with kind IN ('vendor','both').
-- vendor_invoice_number is the number that appears on the vendor's own invoice.
-- ---------------------------------------------------------------------------
CREATE TABLE bills (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id               UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    -- Set by trg_bill_number_seq on INSERT; placeholder overwritten immediately
    bill_number             TEXT NOT NULL DEFAULT '',
    currency                CHAR(3) NOT NULL DEFAULT 'USD',
    subtotal                NUMERIC(15,2) NOT NULL DEFAULT 0,
    tax_total               NUMERIC(15,2) NOT NULL DEFAULT 0,
    total                   NUMERIC(15,2) NOT NULL DEFAULT 0,
    status                  bill_status NOT NULL DEFAULT 'draft',
    issue_date              DATE,
    due_date                DATE,
    paid_at                 TIMESTAMPTZ,
    -- The vendor's own invoice reference number (for reconciliation)
    vendor_invoice_number   TEXT,
    notes                   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at              TIMESTAMPTZ,
    UNIQUE (tenant_id, bill_number),
    CONSTRAINT ck_bills_subtotal_pos    CHECK (subtotal >= 0),
    CONSTRAINT ck_bills_tax_total_pos   CHECK (tax_total >= 0),
    CONSTRAINT ck_bills_total_pos       CHECK (total >= 0),
    CONSTRAINT ck_bills_dates           CHECK (due_date IS NULL OR issue_date IS NULL OR due_date >= issue_date)
);

ALTER TABLE bills ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON bills
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON bills
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_bills_tenant_status   ON bills(tenant_id, status)     WHERE deleted_at IS NULL;
CREATE INDEX idx_bills_tenant_client   ON bills(tenant_id, client_id)  WHERE deleted_at IS NULL;
CREATE INDEX idx_bills_tenant_due_date ON bills(tenant_id, due_date)   WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- bill_lines
-- Each line on a bill.  account_id maps to the expense account to debit.
-- ---------------------------------------------------------------------------
CREATE TABLE bill_lines (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    bill_id         UUID NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    description     TEXT NOT NULL,
    quantity        NUMERIC(10,2) NOT NULL DEFAULT 1,
    unit_price      NUMERIC(15,2) NOT NULL,
    amount          NUMERIC(15,2) NOT NULL,
    -- Optional tax linkage
    tax_rate_id     UUID REFERENCES tax_rates(id) ON DELETE SET NULL,
    tax_amount      NUMERIC(15,2) NOT NULL DEFAULT 0,
    -- Expense account to debit on approval (defaults to 5000 Expenses if NULL)
    account_id      UUID REFERENCES accounts(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_bl_quantity_pos    CHECK (quantity > 0),
    CONSTRAINT ck_bl_unit_price_pos  CHECK (unit_price >= 0),
    CONSTRAINT ck_bl_amount_pos      CHECK (amount >= 0),
    CONSTRAINT ck_bl_tax_amount_pos  CHECK (tax_amount >= 0)
);

ALTER TABLE bill_lines ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON bill_lines
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE INDEX idx_bill_lines_bill_id   ON bill_lines(bill_id);
CREATE INDEX idx_bill_lines_tenant_id ON bill_lines(tenant_id);

-- ---------------------------------------------------------------------------
-- Bill number sequence trigger
--
-- On INSERT into bills:
--   1. Ensure bill_number_sequences row exists for this tenant.
--   2. Atomically increment last_number and read back the new value.
--   3. Format as 'BILL-0001', 'BILL-0042', etc.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_next_bill_number(p_tenant_id UUID)
RETURNS TEXT LANGUAGE plpgsql AS $$
DECLARE
    v_next INTEGER;
BEGIN
    -- Ensure sequence row exists
    INSERT INTO bill_number_sequences (tenant_id, last_number)
    VALUES (p_tenant_id, 0)
    ON CONFLICT (tenant_id) DO NOTHING;

    -- Atomic increment + read
    UPDATE bill_number_sequences
       SET last_number = last_number + 1
     WHERE tenant_id = p_tenant_id
    RETURNING last_number INTO v_next;

    RETURN 'BILL-' || LPAD(v_next::TEXT, 4, '0');
END;
$$;

CREATE OR REPLACE FUNCTION trg_fn_bill_number_seq()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- Only generate when the number has not already been supplied
    IF NEW.bill_number IS NULL OR NEW.bill_number = '' THEN
        NEW.bill_number := fn_next_bill_number(NEW.tenant_id);
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_bill_number_seq
    BEFORE INSERT ON bills
    FOR EACH ROW EXECUTE FUNCTION trg_fn_bill_number_seq();

COMMIT;
