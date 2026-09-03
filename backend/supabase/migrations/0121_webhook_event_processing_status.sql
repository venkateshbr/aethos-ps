-- =============================================================================
-- Migration 0121: webhook_events.processing_status  (issue #493)
--
-- The Stripe webhook handler used to wrap `_dispatch` in `except Exception:`,
-- log, then unconditionally write the idempotency row and return HTTP 200. A
-- `checkout.session.completed` whose payment/journal write failed (transient
-- Supabase error, locked period rejected by the accounting guardian, FK
-- violation) was therefore acknowledged to Stripe, never retried, and skipped
-- on redelivery by the idempotency guard: cash collected, nothing in the
-- ledger.
--
-- Recording the outcome lets the endpoint (a) return 5xx so Stripe retries and
-- (b) re-attempt a previously failed event on redelivery, while still keeping
-- the audit row for every delivery we saw.
-- =============================================================================

BEGIN;

ALTER TABLE webhook_events
    ADD COLUMN IF NOT EXISTS processing_status TEXT NOT NULL DEFAULT 'processed',
    ADD COLUMN IF NOT EXISTS error_class       TEXT,
    ADD COLUMN IF NOT EXISTS attempts          INTEGER NOT NULL DEFAULT 1;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'webhook_events_processing_status_check'
    ) THEN
        ALTER TABLE webhook_events
            ADD CONSTRAINT webhook_events_processing_status_check
            CHECK (processing_status IN ('processed', 'failed'));
    END IF;
END $$;

-- Operators triage failures from Settings -> Operational Health and the
-- /api/v1/webhook-events API; keep that filter cheap.
CREATE INDEX IF NOT EXISTS ix_webhook_events_processing_status
    ON webhook_events (processing_status)
    WHERE processing_status <> 'processed';

COMMENT ON COLUMN webhook_events.processing_status IS
    'processed = handler completed; failed = handler raised, Stripe was asked to retry (#493).';
COMMENT ON COLUMN webhook_events.attempts IS
    'Delivery attempts seen for this provider_event_id; incremented on each retry.';

COMMIT;
