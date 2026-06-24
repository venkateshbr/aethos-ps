-- =============================================================================
-- Migration 0067: Engagement Per-Unit Billing Terms
-- =============================================================================
-- Adds generic unit billing fields so payroll-per-employee, per-entity, and
-- per-event services can retain unit economics while remaining compatible with
-- fixed-fee invoicing/reporting.
-- =============================================================================

BEGIN;

ALTER TABLE engagement_billing_terms
    ADD COLUMN IF NOT EXISTS billing_unit TEXT,
    ADD COLUMN IF NOT EXISTS unit_label TEXT,
    ADD COLUMN IF NOT EXISTS unit_quantity NUMERIC(12,2),
    ADD COLUMN IF NOT EXISTS unit_price NUMERIC(15,2);

DO $$
BEGIN
    ALTER TABLE engagement_billing_terms
        ADD CONSTRAINT ck_ebt_billing_unit
        CHECK (
            billing_unit IS NULL
            OR billing_unit IN (
                'hour', 'fixed', 'retainer', 'per_employee',
                'per_entity', 'per_event', 'milestone'
            )
        );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE engagement_billing_terms
        ADD CONSTRAINT ck_ebt_unit_quantity_pos
        CHECK (unit_quantity IS NULL OR unit_quantity >= 0);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE engagement_billing_terms
        ADD CONSTRAINT ck_ebt_unit_price_pos
        CHECK (unit_price IS NULL OR unit_price >= 0);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

COMMIT;
