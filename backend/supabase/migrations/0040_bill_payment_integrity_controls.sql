-- =============================================================================
-- Migration 0040: Bill Payment Integrity Controls
--
-- Adds actor/timestamp and file-integrity metadata to bill payment batches, then
-- records approval/export/send/settlement transitions into financial_events.
-- =============================================================================

BEGIN;

ALTER TYPE batch_status ADD VALUE IF NOT EXISTS 'settled';

ALTER TABLE bill_payment_batches
    ADD COLUMN approved_by UUID,
    ADD COLUMN approved_at TIMESTAMPTZ,
    ADD COLUMN exported_by UUID,
    ADD COLUMN export_file_sha256 TEXT,
    ADD COLUMN export_file_bytes INTEGER,
    ADD COLUMN sent_by UUID,
    ADD COLUMN sent_at TIMESTAMPTZ,
    ADD COLUMN settled_by UUID,
    ADD COLUMN settled_at TIMESTAMPTZ,
    ADD CONSTRAINT ck_bill_payment_export_hash CHECK (
        export_file_sha256 IS NULL OR export_file_sha256 ~ '^[0-9a-f]{64}$'
    ),
    ADD CONSTRAINT ck_bill_payment_export_bytes CHECK (
        export_file_bytes IS NULL OR export_file_bytes >= 0
    );

CREATE INDEX idx_bill_payment_batches_export_hash
    ON bill_payment_batches(tenant_id, export_file_sha256)
    WHERE export_file_sha256 IS NOT NULL;

CREATE OR REPLACE FUNCTION trg_log_bill_payment_batch_event()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_event_type TEXT;
    v_action TEXT;
    v_actor_user_id TEXT;
    v_idempotency_key TEXT;
BEGIN
    IF OLD.export_file_sha256 IS DISTINCT FROM NEW.export_file_sha256
       AND NEW.export_file_sha256 IS NOT NULL THEN
        v_event_type := 'bill_payment.exported';
        v_action := 'exported';
        v_actor_user_id := NEW.exported_by::TEXT;
        v_idempotency_key := 'bill_payment.exported:' || NEW.id::TEXT || ':' || NEW.export_file_sha256;
    ELSIF OLD.status IS DISTINCT FROM NEW.status AND NEW.status::TEXT = 'approved' THEN
        v_event_type := 'bill_payment.approved';
        v_action := 'approved';
        v_actor_user_id := NEW.approved_by::TEXT;
        v_idempotency_key := 'bill_payment.approved:' || NEW.id::TEXT;
    ELSIF OLD.status IS DISTINCT FROM NEW.status AND NEW.status::TEXT = 'sent_to_bank' THEN
        v_event_type := 'bill_payment.sent_to_bank';
        v_action := 'sent_to_bank';
        v_actor_user_id := NEW.sent_by::TEXT;
        v_idempotency_key := 'bill_payment.sent_to_bank:' || NEW.id::TEXT;
    ELSIF OLD.status IS DISTINCT FROM NEW.status AND NEW.status::TEXT = 'settled' THEN
        v_event_type := 'bill_payment.settled';
        v_action := 'settled';
        v_actor_user_id := NEW.settled_by::TEXT;
        v_idempotency_key := 'bill_payment.settled:' || NEW.id::TEXT;
    ELSE
        RETURN NEW;
    END IF;

    PERFORM append_financial_event(
        NEW.tenant_id,
        v_event_type,
        'bill_payment_batch',
        NEW.id::TEXT,
        'bill_payment_batch',
        NEW.id::TEXT,
        v_actor_user_id,
        NULL,
        v_action,
        TO_JSONB(OLD),
        TO_JSONB(NEW),
        jsonb_build_object(
            'status', NEW.status,
            'file_format', NEW.file_format,
            'export_file_sha256', NEW.export_file_sha256,
            'export_file_bytes', NEW.export_file_bytes,
            'total', NEW.total,
            'currency', NEW.currency
        ),
        v_idempotency_key
    );
    RETURN NEW;
END;
$$;

CREATE TRIGGER log_bill_payment_batch_event
    AFTER UPDATE ON bill_payment_batches
    FOR EACH ROW
    EXECUTE FUNCTION trg_log_bill_payment_batch_event();

REVOKE ALL ON FUNCTION trg_log_bill_payment_batch_event() FROM PUBLIC;

COMMIT;
