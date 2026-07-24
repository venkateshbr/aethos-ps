-- =============================================================================
-- Migration 0114: Bill-payment export template-safety guard (issue #404)
--
-- NACHA/CSV exports today emit PLACEHOLDER routing/account values (the firm's
-- real funding account is never stored here — Prahari gate). Nothing stopped a
-- placeholder "template" file from being marked sent_to_bank, so a zeros/placeholder
-- instruction could be represented as a real payment. This adds:
--   * export_is_template  — true when the last export contained placeholder bank
--     data (the only mode today); the operator must complete + confirm it.
--   * bank_details_confirmed_at / _by — the operator's attestation that the real
--     routing/account were filled in (in their bank portal) for this export.
-- mark_sent is gated on these in the service layer. Idempotent.
-- =============================================================================

BEGIN;

ALTER TABLE bill_payment_batches
    ADD COLUMN IF NOT EXISTS export_is_template BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS bank_details_confirmed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS bank_details_confirmed_by UUID;

COMMENT ON COLUMN bill_payment_batches.export_is_template IS
    'True when the last export used placeholder routing/account data (#404); such a '
    'batch cannot be marked sent_to_bank until bank_details_confirmed_at is set.';

COMMIT;
