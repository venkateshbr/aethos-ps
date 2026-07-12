-- =============================================================================
-- Migration 0102: Freeze invoice/bill approval FX amounts and provenance
-- =============================================================================
-- New columns remain nullable so documents approved before this migration stay
-- readable. Same-currency historical documents can be backfilled exactly;
-- foreign-currency history is intentionally left NULL rather than reconstructed
-- from a rate that may not have been used by the original posting.
-- =============================================================================

BEGIN;

ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS base_currency CHAR(3),
    ADD COLUMN IF NOT EXISTS base_subtotal NUMERIC(15,2),
    ADD COLUMN IF NOT EXISTS base_tax_total NUMERIC(15,2),
    ADD COLUMN IF NOT EXISTS base_total NUMERIC(15,2),
    ADD COLUMN IF NOT EXISTS approval_fx_rate_id UUID;

ALTER TABLE bills
    ADD COLUMN IF NOT EXISTS base_currency CHAR(3),
    ADD COLUMN IF NOT EXISTS base_subtotal NUMERIC(15,2),
    ADD COLUMN IF NOT EXISTS base_tax_total NUMERIC(15,2),
    ADD COLUMN IF NOT EXISTS base_total NUMERIC(15,2),
    ADD COLUMN IF NOT EXISTS approval_fx_rate_id UUID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_invoices_approval_fx_rate'
          AND conrelid = 'invoices'::regclass
    ) THEN
        ALTER TABLE invoices
            ADD CONSTRAINT fk_invoices_approval_fx_rate
            FOREIGN KEY (approval_fx_rate_id) REFERENCES fx_rates(id)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_bills_approval_fx_rate'
          AND conrelid = 'bills'::regclass
    ) THEN
        ALTER TABLE bills
            ADD CONSTRAINT fk_bills_approval_fx_rate
            FOREIGN KEY (approval_fx_rate_id) REFERENCES fx_rates(id)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_invoices_base_amounts_nonnegative'
          AND conrelid = 'invoices'::regclass
    ) THEN
        ALTER TABLE invoices
            ADD CONSTRAINT ck_invoices_base_amounts_nonnegative CHECK (
                (base_subtotal IS NULL OR base_subtotal >= 0)
                AND (base_tax_total IS NULL OR base_tax_total >= 0)
                AND (base_total IS NULL OR base_total >= 0)
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_bills_base_amounts_nonnegative'
          AND conrelid = 'bills'::regclass
    ) THEN
        ALTER TABLE bills
            ADD CONSTRAINT ck_bills_base_amounts_nonnegative CHECK (
                (base_subtotal IS NULL OR base_subtotal >= 0)
                AND (base_tax_total IS NULL OR base_tax_total >= 0)
                AND (base_total IS NULL OR base_total >= 0)
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_invoices_base_amounts_complete'
          AND conrelid = 'invoices'::regclass
    ) THEN
        ALTER TABLE invoices
            ADD CONSTRAINT ck_invoices_base_amounts_complete CHECK (
                (
                    base_currency IS NULL
                    AND base_subtotal IS NULL
                    AND base_tax_total IS NULL
                    AND base_total IS NULL
                    AND approval_fx_rate_id IS NULL
                )
                OR (
                    base_currency IS NOT NULL
                    AND base_subtotal IS NOT NULL
                    AND base_tax_total IS NOT NULL
                    AND base_total = base_subtotal + base_tax_total
                    AND (
                        (UPPER(currency) = UPPER(base_currency) AND approval_fx_rate_id IS NULL)
                        OR (
                            UPPER(currency) <> UPPER(base_currency)
                            AND approval_fx_rate_id IS NOT NULL
                        )
                    )
                )
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_bills_base_amounts_complete'
          AND conrelid = 'bills'::regclass
    ) THEN
        ALTER TABLE bills
            ADD CONSTRAINT ck_bills_base_amounts_complete CHECK (
                (
                    base_currency IS NULL
                    AND base_subtotal IS NULL
                    AND base_tax_total IS NULL
                    AND base_total IS NULL
                    AND approval_fx_rate_id IS NULL
                )
                OR (
                    base_currency IS NOT NULL
                    AND base_subtotal IS NOT NULL
                    AND base_tax_total IS NOT NULL
                    AND base_total = base_subtotal + base_tax_total
                    AND (
                        (UPPER(currency) = UPPER(base_currency) AND approval_fx_rate_id IS NULL)
                        OR (
                            UPPER(currency) <> UPPER(base_currency)
                            AND approval_fx_rate_id IS NOT NULL
                        )
                    )
                )
            );
    END IF;
END
$$;

-- Same-currency history is losslessly backfillable at rate 1. Foreign-currency
-- history remains NULL because guessing an approval rate would corrupt audit
-- provenance and realised-gain/loss calculations.
UPDATE invoices i
SET base_currency = t.base_currency,
    base_subtotal = i.subtotal,
    base_tax_total = i.tax_total,
    base_total = i.total
FROM tenants t
WHERE i.tenant_id = t.id
  AND UPPER(i.currency) = UPPER(t.base_currency)
  AND i.status <> 'draft'
  AND (
      i.base_currency IS NULL
      OR i.base_subtotal IS NULL
      OR i.base_tax_total IS NULL
      OR i.base_total IS NULL
  );

UPDATE bills b
SET base_currency = t.base_currency,
    base_subtotal = b.subtotal,
    base_tax_total = b.tax_total,
    base_total = b.total
FROM tenants t
WHERE b.tenant_id = t.id
  AND UPPER(b.currency) = UPPER(t.base_currency)
  AND b.status <> 'draft'
  AND (
      b.base_currency IS NULL
      OR b.base_subtotal IS NULL
      OR b.base_tax_total IS NULL
      OR b.base_total IS NULL
  );

COMMIT;
