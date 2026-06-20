-- ---------------------------------------------------------------------------
-- Migration 0029: Contacts — ensure client_kind includes 'both'
--
-- The client_kind enum was defined with 'both' in the baseline migration
-- (0001_tenants_auth.sql). This migration is idempotent: it ensures the
-- value exists even if this DB was initialised from a snapshot that omitted
-- it, and updates the table comment to reflect the expanded semantics.
--
-- PostgreSQL 9.6+ supports ALTER TYPE ... ADD VALUE IF NOT EXISTS.
-- Supabase runs PostgreSQL 15+ so this syntax is safe.
-- ---------------------------------------------------------------------------

DO $$
BEGIN
    -- Only add the value if it is not already present in the enum.
    IF NOT EXISTS (
        SELECT 1
        FROM pg_enum e
        JOIN pg_type t ON e.enumtypid = t.oid
        WHERE t.typname = 'client_kind'
          AND e.enumlabel = 'both'
    ) THEN
        ALTER TYPE client_kind ADD VALUE 'both';
    END IF;
END
$$;

-- Update table comment to reflect expanded contact semantics
COMMENT ON TABLE clients IS 'Contacts — customers, vendors, or both (kind discriminator)';
