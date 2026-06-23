-- =============================================================================
-- Migration 0071: Rate Card Service-Line Segmentation
-- =============================================================================
-- Allows a rate card to carry a generic role rate plus service-line-specific
-- role rates. Invoice drafting resolves exact service-line rates first and
-- falls back to the generic role rate.
-- =============================================================================

BEGIN;

ALTER TABLE rate_card_lines
    ADD COLUMN IF NOT EXISTS service_line TEXT;

ALTER TABLE rate_card_client_overrides
    ADD COLUMN IF NOT EXISTS service_line TEXT;

ALTER TABLE rate_card_lines
    DROP CONSTRAINT IF EXISTS rate_card_lines_rate_card_id_role_key;

DO $$
BEGIN
    ALTER TABLE rate_card_lines
        ADD CONSTRAINT ck_rate_card_lines_service_line
        CHECK (
            service_line IS NULL
            OR service_line IN ('accounting', 'tax', 'cosec', 'payroll', 'advisory', 'other')
        );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE rate_card_client_overrides
        ADD CONSTRAINT ck_rcco_service_line
        CHECK (
            service_line IS NULL
            OR service_line IN ('accounting', 'tax', 'cosec', 'payroll', 'advisory', 'other')
        );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS idx_rate_card_lines_role_service_line
    ON rate_card_lines(rate_card_id, role, COALESCE(service_line, ''));

CREATE INDEX IF NOT EXISTS idx_rcco_role_service_line
    ON rate_card_client_overrides(tenant_id, rate_card_id, client_id, role, service_line);

COMMIT;
