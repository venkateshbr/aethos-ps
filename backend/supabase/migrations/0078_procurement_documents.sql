-- Procurement documents for PO/service-order controlled accounts payable.

BEGIN;

CREATE TABLE IF NOT EXISTS procurement_document_number_sequences (
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_type TEXT NOT NULL,
    last_number   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, document_type),
    CONSTRAINT ck_procurement_document_sequence_type
        CHECK (document_type IN ('purchase_order', 'service_order'))
);

ALTER TABLE procurement_document_number_sequences ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "tenant_isolation" ON procurement_document_number_sequences;
CREATE POLICY "tenant_isolation" ON procurement_document_number_sequences
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TABLE IF NOT EXISTS procurement_documents (
    id                         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_type              TEXT NOT NULL DEFAULT 'purchase_order',
    document_number            TEXT NOT NULL DEFAULT '',
    client_id                  UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    status                     TEXT NOT NULL DEFAULT 'draft',
    currency                   CHAR(3) NOT NULL DEFAULT 'USD',
    issue_date                 DATE,
    expected_delivery_date     DATE,
    service_start_date         DATE,
    service_end_date           DATE,
    subtotal                   NUMERIC(15,2) NOT NULL DEFAULT 0,
    tax_total                  NUMERIC(15,2) NOT NULL DEFAULT 0,
    total                      NUMERIC(15,2) NOT NULL DEFAULT 0,
    matched_bill_total         NUMERIC(15,2) NOT NULL DEFAULT 0,
    requested_by               TEXT,
    approved_by                TEXT,
    approved_at                TIMESTAMPTZ,
    notes                      TEXT,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at                 TIMESTAMPTZ,
    UNIQUE (tenant_id, document_number),
    CONSTRAINT ck_procurement_documents_type
        CHECK (document_type IN ('purchase_order', 'service_order')),
    CONSTRAINT ck_procurement_documents_status
        CHECK (status IN ('draft', 'submitted', 'approved', 'closed', 'cancelled')),
    CONSTRAINT ck_procurement_documents_totals
        CHECK (subtotal >= 0 AND tax_total >= 0 AND total >= 0 AND matched_bill_total >= 0),
    CONSTRAINT ck_procurement_documents_delivery_date
        CHECK (expected_delivery_date IS NULL OR issue_date IS NULL OR expected_delivery_date >= issue_date),
    CONSTRAINT ck_procurement_documents_service_dates
        CHECK (service_end_date IS NULL OR service_start_date IS NULL OR service_end_date >= service_start_date)
);

ALTER TABLE procurement_documents ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "tenant_isolation" ON procurement_documents;
CREATE POLICY "tenant_isolation" ON procurement_documents
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON procurement_documents
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX IF NOT EXISTS idx_procurement_documents_tenant_status
    ON procurement_documents (tenant_id, status)
    WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_procurement_documents_tenant_client
    ON procurement_documents (tenant_id, client_id)
    WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS procurement_document_lines (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    procurement_document_id UUID NOT NULL REFERENCES procurement_documents(id) ON DELETE CASCADE,
    description             TEXT NOT NULL,
    quantity                NUMERIC(10,2) NOT NULL DEFAULT 1,
    unit_price              NUMERIC(15,2) NOT NULL,
    amount                  NUMERIC(15,2) NOT NULL,
    tax_amount              NUMERIC(15,2) NOT NULL DEFAULT 0,
    account_id              UUID REFERENCES accounts(id) ON DELETE SET NULL,
    service_start_date      DATE,
    service_end_date        DATE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_procurement_document_lines_quantity CHECK (quantity > 0),
    CONSTRAINT ck_procurement_document_lines_amounts CHECK (unit_price >= 0 AND amount >= 0 AND tax_amount >= 0),
    CONSTRAINT ck_procurement_document_lines_service_dates
        CHECK (service_end_date IS NULL OR service_start_date IS NULL OR service_end_date >= service_start_date)
);

ALTER TABLE procurement_document_lines ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "tenant_isolation" ON procurement_document_lines;
CREATE POLICY "tenant_isolation" ON procurement_document_lines
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE INDEX IF NOT EXISTS idx_procurement_document_lines_document
    ON procurement_document_lines (procurement_document_id);

CREATE OR REPLACE FUNCTION fn_next_procurement_document_number(
    p_tenant_id UUID,
    p_document_type TEXT
)
RETURNS TEXT LANGUAGE plpgsql AS $$
DECLARE
    v_next INTEGER;
    v_prefix TEXT;
BEGIN
    INSERT INTO procurement_document_number_sequences (tenant_id, document_type, last_number)
    VALUES (p_tenant_id, p_document_type, 0)
    ON CONFLICT (tenant_id, document_type) DO NOTHING;

    UPDATE procurement_document_number_sequences
       SET last_number = last_number + 1
     WHERE tenant_id = p_tenant_id
       AND document_type = p_document_type
    RETURNING last_number INTO v_next;

    v_prefix := CASE p_document_type
        WHEN 'service_order' THEN 'SO'
        ELSE 'PO'
    END;

    RETURN v_prefix || '-' || LPAD(v_next::TEXT, 4, '0');
END;
$$;

CREATE OR REPLACE FUNCTION trg_fn_procurement_document_number_seq()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.document_number IS NULL OR NEW.document_number = '' THEN
        NEW.document_number := fn_next_procurement_document_number(
            NEW.tenant_id,
            NEW.document_type
        );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_procurement_document_number_seq ON procurement_documents;
CREATE TRIGGER trg_procurement_document_number_seq
    BEFORE INSERT ON procurement_documents
    FOR EACH ROW EXECUTE FUNCTION trg_fn_procurement_document_number_seq();

ALTER TABLE bills
    ADD COLUMN IF NOT EXISTS purchase_order_id UUID REFERENCES procurement_documents(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS po_match_status TEXT NOT NULL DEFAULT 'not_linked',
    ADD COLUMN IF NOT EXISTS po_match_summary JSONB NOT NULL DEFAULT '{}'::JSONB;

ALTER TABLE bills DROP CONSTRAINT IF EXISTS ck_bills_po_match_status;
ALTER TABLE bills
    ADD CONSTRAINT ck_bills_po_match_status
    CHECK (po_match_status IN (
        'not_linked',
        'matched',
        'over_tolerance',
        'vendor_mismatch',
        'currency_mismatch',
        'order_not_approved',
        'order_not_found'
    ));

CREATE INDEX IF NOT EXISTS idx_bills_tenant_purchase_order
    ON bills (tenant_id, purchase_order_id)
    WHERE deleted_at IS NULL AND purchase_order_id IS NOT NULL;

COMMIT;
