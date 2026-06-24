-- Vendor onboarding controls for procure-to-pay launch readiness.
--
-- The clients table is the system of record for both customers and vendors.
-- These fields make vendor payment readiness explicit before AP payment runs
-- can rely on a vendor contact.

ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS vendor_onboarding_status TEXT NOT NULL DEFAULT 'not_required',
    ADD COLUMN IF NOT EXISTS vendor_bank_account_status TEXT NOT NULL DEFAULT 'not_provided',
    ADD COLUMN IF NOT EXISTS vendor_tax_validation_status TEXT NOT NULL DEFAULT 'not_checked',
    ADD COLUMN IF NOT EXISTS vendor_sanctions_status TEXT NOT NULL DEFAULT 'not_checked',
    ADD COLUMN IF NOT EXISTS vendor_remittance_status TEXT NOT NULL DEFAULT 'not_configured',
    ADD COLUMN IF NOT EXISTS vendor_remittance_email TEXT,
    ADD COLUMN IF NOT EXISTS vendor_payment_controls JSONB NOT NULL DEFAULT '{}'::JSONB,
    ADD COLUMN IF NOT EXISTS vendor_onboarding_approved_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS vendor_onboarding_approved_by TEXT;

ALTER TABLE clients DROP CONSTRAINT IF EXISTS ck_clients_vendor_onboarding_status;
ALTER TABLE clients
    ADD CONSTRAINT ck_clients_vendor_onboarding_status
    CHECK (vendor_onboarding_status IN ('not_required', 'pending', 'approved', 'blocked'));

ALTER TABLE clients DROP CONSTRAINT IF EXISTS ck_clients_vendor_bank_account_status;
ALTER TABLE clients
    ADD CONSTRAINT ck_clients_vendor_bank_account_status
    CHECK (vendor_bank_account_status IN ('not_provided', 'pending_verification', 'verified', 'failed'));

ALTER TABLE clients DROP CONSTRAINT IF EXISTS ck_clients_vendor_tax_validation_status;
ALTER TABLE clients
    ADD CONSTRAINT ck_clients_vendor_tax_validation_status
    CHECK (vendor_tax_validation_status IN ('not_checked', 'valid', 'warning', 'failed'));

ALTER TABLE clients DROP CONSTRAINT IF EXISTS ck_clients_vendor_sanctions_status;
ALTER TABLE clients
    ADD CONSTRAINT ck_clients_vendor_sanctions_status
    CHECK (vendor_sanctions_status IN ('not_checked', 'clear', 'potential_match', 'blocked'));

ALTER TABLE clients DROP CONSTRAINT IF EXISTS ck_clients_vendor_remittance_status;
ALTER TABLE clients
    ADD CONSTRAINT ck_clients_vendor_remittance_status
    CHECK (vendor_remittance_status IN ('not_configured', 'configured', 'verified', 'blocked'));

UPDATE clients
SET vendor_onboarding_status = 'pending'
WHERE kind IN ('vendor', 'both')
  AND vendor_onboarding_status = 'not_required';

CREATE INDEX IF NOT EXISTS idx_clients_vendor_onboarding_status
    ON clients (tenant_id, vendor_onboarding_status)
    WHERE deleted_at IS NULL AND kind IN ('vendor', 'both');
