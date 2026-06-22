-- =============================================================================
-- Migration 0048: Rate Cards Authenticated Read RLS
--
-- Continue service-role reduction for rate-card read surfaces. Admin-only
-- create remains API-gated and service-role backed; authenticated tenant
-- members can read rate cards and their line rates through RLS.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON rate_cards;
DROP POLICY IF EXISTS "authenticated_member_read" ON rate_card_lines;

CREATE POLICY "authenticated_member_read" ON rate_cards
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE POLICY "authenticated_member_read" ON rate_card_lines
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
