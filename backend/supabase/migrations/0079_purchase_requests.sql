-- Extend procurement documents to cover purchase-request intake and conversion.

BEGIN;

ALTER TABLE procurement_documents
    ADD COLUMN IF NOT EXISTS source_request_id UUID REFERENCES procurement_documents(id) ON DELETE SET NULL;

ALTER TABLE procurement_document_number_sequences
    DROP CONSTRAINT IF EXISTS ck_procurement_document_sequence_type;
ALTER TABLE procurement_document_number_sequences
    ADD CONSTRAINT ck_procurement_document_sequence_type
    CHECK (document_type IN ('purchase_request', 'purchase_order', 'service_order'));

ALTER TABLE procurement_documents
    DROP CONSTRAINT IF EXISTS ck_procurement_documents_type;
ALTER TABLE procurement_documents
    ADD CONSTRAINT ck_procurement_documents_type
    CHECK (document_type IN ('purchase_request', 'purchase_order', 'service_order'));

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
        WHEN 'purchase_request' THEN 'PR'
        WHEN 'service_order' THEN 'SO'
        ELSE 'PO'
    END;

    RETURN v_prefix || '-' || LPAD(v_next::TEXT, 4, '0');
END;
$$;

CREATE INDEX IF NOT EXISTS idx_procurement_documents_source_request
    ON procurement_documents (tenant_id, source_request_id)
    WHERE deleted_at IS NULL AND source_request_id IS NOT NULL;

COMMIT;
