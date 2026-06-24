-- Store deterministic payment-run optimization context on bill payment batches.

ALTER TABLE bill_payment_batches
    ADD COLUMN IF NOT EXISTS optimization_summary JSONB NOT NULL DEFAULT '{}'::JSONB,
    ADD COLUMN IF NOT EXISTS risk_review_required BOOLEAN NOT NULL DEFAULT FALSE;
