-- =============================================================================
-- Migration 0020: tenant_users — add self-read RLS policy
-- Issue: #128
-- =============================================================================
-- Root cause: The LoginComponent calls the Supabase JS client (anon/authenticated
-- key) to query tenant_users and look up the user's tenant_id.  The only existing
-- policy — "tenant_isolation" — requires app.current_tenant_id to already be set
-- in the session, which is never the case in a browser-side unauthenticated or
-- newly-authenticated context.  The anon/authenticated caller therefore gets zero
-- rows and the login flow treats this as "no tenant" and rejects the user.
--
-- Fix: add a supplemental PERMISSIVE SELECT policy that lets each authenticated
-- Supabase user read only their own membership rows (user_id = auth.uid()).
-- This does NOT expose other tenants' rows — the predicate is per-user.
-- The service-role client used by the backend bypasses RLS entirely; this policy
-- only affects anon/authenticated callers (i.e. the browser-side Supabase JS
-- client used by LoginComponent).
-- =============================================================================

BEGIN;

CREATE POLICY "user_can_read_own_memberships" ON tenant_users
    FOR SELECT
    USING (user_id = auth.uid());

COMMIT;
