-- =============================================================================
-- Migration 0070: Invoice Adjustment Lines
-- =============================================================================
-- Capped T&M and retainer-draw invoices need negative adjustment lines while
-- the invoice header total remains non-negative. Existing header constraints
-- continue to block negative invoices; only line-level signs are relaxed.
-- =============================================================================

BEGIN;

ALTER TABLE invoice_lines
    DROP CONSTRAINT IF EXISTS ck_il_unit_price_pos,
    DROP CONSTRAINT IF EXISTS ck_il_amount_pos;

COMMIT;
