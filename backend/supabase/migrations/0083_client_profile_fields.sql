-- =============================================================================
-- Migration 0083: Contact profile fields
-- =============================================================================
-- Adds explicit contact profile fields used by the browser create/edit flows.
-- Email is stored in the existing clients.billing_email column.
-- =============================================================================

BEGIN;

ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS phone TEXT;

ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS website TEXT;

COMMIT;
