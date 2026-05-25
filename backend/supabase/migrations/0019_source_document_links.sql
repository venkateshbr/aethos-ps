-- 0019_source_document_links.sql
-- Add source-document FK to engagements + bills so HITL-approved
-- materialised rows carry a link back to the original uploaded file.
-- project_expenses.document_id already exists from migration 0007.
-- See #127.

BEGIN;

ALTER TABLE engagements
    ADD COLUMN IF NOT EXISTS source_document_id UUID
        REFERENCES documents(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_engagements_source_document
    ON engagements(source_document_id)
    WHERE source_document_id IS NOT NULL;

ALTER TABLE bills
    ADD COLUMN IF NOT EXISTS source_document_id UUID
        REFERENCES documents(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_bills_source_document
    ON bills(source_document_id)
    WHERE source_document_id IS NOT NULL;

COMMIT;
