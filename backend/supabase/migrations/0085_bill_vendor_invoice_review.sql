-- =============================================================================
-- Migration 0085: Vendor Invoice Review Evidence
--
-- Preserve AI vendor-match, coding, duplicate, and exception review evidence on
-- bills materialised from Inbox-reviewed vendor invoices.
-- =============================================================================

BEGIN;

ALTER TABLE bills
    ADD COLUMN IF NOT EXISTS vendor_invoice_review JSONB NOT NULL DEFAULT '{}'::JSONB;

COMMENT ON COLUMN bills.vendor_invoice_review IS
    'Reviewed AI extraction evidence for vendor invoices: vendor match, coding suggestions, duplicate review, exceptions, and source document metadata.';

COMMIT;
