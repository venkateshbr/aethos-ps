-- =============================================================================
-- Migration 0050: Time Entries Authenticated Read RLS
--
-- Continue service-role reduction for time-entry read surfaces. Time-entry
-- create/update/delete remain API-gated and service-role backed because they
-- enforce period locks, tenant-scoped FK checks, and billed-entry guards.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON time_entries;

CREATE POLICY "authenticated_member_read" ON time_entries
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
