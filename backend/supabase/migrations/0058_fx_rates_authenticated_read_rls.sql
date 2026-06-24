-- =============================================================================
-- Migration 0058: FX Rates Authenticated Read RLS
--
-- FX rates are global reference data with no tenant_id. Authenticated API users
-- may read rates through the anon/JWT client; service-role remains reserved for
-- the refresh worker upsert path.
-- =============================================================================

BEGIN;

ALTER TABLE fx_rates ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "authenticated_read" ON fx_rates;

CREATE POLICY "authenticated_read" ON fx_rates
    FOR SELECT
    TO authenticated
    USING (TRUE);

COMMIT;
