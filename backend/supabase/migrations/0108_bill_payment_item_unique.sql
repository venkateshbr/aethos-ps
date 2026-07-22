-- =============================================================================
-- Migration 0108: Prevent double-settlement of a bill (issue #391 / LR-10)
--
-- bill_payment_items had no uniqueness on bill_id, so the same approved bill
-- could be pulled into two concurrent payment batches and settled twice
-- (double DR AP / CR Bank). A bill is paid in full in a single batch (partial AP
-- payments are not supported), so a bill may belong to at most ONE active
-- (non-cancelled) payment item. This partial unique index is the data-layer
-- backstop for the app-level pre-filter in bill_payments_service.
-- Idempotent (safe to re-apply).
-- =============================================================================

BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS ux_bill_payment_items_active_bill
    ON bill_payment_items (bill_id)
    WHERE status IS DISTINCT FROM 'cancelled';

COMMENT ON INDEX ux_bill_payment_items_active_bill IS
    'One active payment item per bill: blocks the same bill entering two batches '
    '(double-settlement). Cancelled items are excluded so a bill can be re-batched.';

COMMIT;
