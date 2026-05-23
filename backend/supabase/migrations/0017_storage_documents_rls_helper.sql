-- =============================================================================
-- Migration 0017: Storage — fix `documents` RLS to bypass inner RLS on
--                 tenant_users via a SECURITY DEFINER helper.
-- Issue: #100  (follow-up to 0016)
-- Owner:  Sthira (SRE)
-- =============================================================================
--
-- Why this exists
-- ---------------
-- Migration 0016 wrote the four `documents_tenant_*` RLS policies as direct
-- EXISTS subqueries against `public.tenant_users`:
--
--     EXISTS (SELECT 1 FROM public.tenant_users
--              WHERE user_id   = auth.uid()
--                AND tenant_id = (storage.foldername(name))[1]::uuid
--                AND deleted_at IS NULL)
--
-- But `public.tenant_users` has its OWN RLS (`tenant_isolation`, written in
-- migration 0001) that requires the session-local GUC
-- `app.current_tenant_id` to be set, and that GUC is **never set** in the
-- GoTrue → Storage path.  Result: the inner subquery returns zero rows for
-- every authenticated caller, the EXISTS evaluates to FALSE, and the legit
-- tenant owner sees a 404 on their own object.  Verified via
-- backend/tests/api/test_storage_rls.py::test_storage_rls_cross_tenant_denial
-- which failed against the 0016 policies.
--
-- The fix
-- -------
-- Wrap the membership lookup in a SECURITY DEFINER SQL function owned by a
-- superuser (the migration runner / postgres role).  SECURITY DEFINER means
-- the function runs with the OWNER's privileges, not the caller's, and so
-- bypasses the `tenant_isolation` RLS on `tenant_users`.  The function is
-- intentionally narrow — `(user_id, tenant_id) -> boolean` — so it can't be
-- abused for general tenant_users enumeration.  Marked STABLE so the
-- planner can cache the result within a single statement.
--
-- This migration is idempotent — `CREATE OR REPLACE FUNCTION` and
-- `DROP POLICY IF EXISTS` + `CREATE POLICY`.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. SECURITY DEFINER membership helper
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.is_tenant_member(
    p_user_id   UUID,
    p_tenant_id UUID
) RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public, pg_temp
AS $$
    SELECT EXISTS (
        SELECT 1
          FROM public.tenant_users tu
         WHERE tu.user_id    = p_user_id
           AND tu.tenant_id  = p_tenant_id
           AND tu.deleted_at IS NULL
    );
$$;

COMMENT ON FUNCTION public.is_tenant_member(UUID, UUID) IS
    'Returns TRUE iff the user has an active (non soft-deleted) row in '
    'tenant_users for the given tenant. SECURITY DEFINER so it bypasses '
    'tenant_users own RLS — used by Storage RLS policies that run under '
    'the authenticated role without app.current_tenant_id set.';

-- Lock down EXECUTE: only the JWT-authenticated role + service role.
REVOKE ALL ON FUNCTION public.is_tenant_member(UUID, UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.is_tenant_member(UUID, UUID)
    TO authenticated, service_role;

-- ---------------------------------------------------------------------------
-- 2. Replace the four `documents_tenant_*` policies on storage.objects
--    to call the helper instead of the inline EXISTS subquery.
-- ---------------------------------------------------------------------------

DROP POLICY IF EXISTS "documents_tenant_select"  ON storage.objects;
DROP POLICY IF EXISTS "documents_tenant_insert"  ON storage.objects;
DROP POLICY IF EXISTS "documents_tenant_update"  ON storage.objects;
DROP POLICY IF EXISTS "documents_tenant_delete"  ON storage.objects;

CREATE POLICY "documents_tenant_select"
    ON storage.objects
    FOR SELECT
    TO authenticated
    USING (
        bucket_id = 'documents'
        AND public.is_tenant_member(
            auth.uid(),
            NULLIF((storage.foldername(name))[1], '')::uuid
        )
    );

CREATE POLICY "documents_tenant_insert"
    ON storage.objects
    FOR INSERT
    TO authenticated
    WITH CHECK (
        bucket_id = 'documents'
        AND public.is_tenant_member(
            auth.uid(),
            NULLIF((storage.foldername(name))[1], '')::uuid
        )
    );

CREATE POLICY "documents_tenant_update"
    ON storage.objects
    FOR UPDATE
    TO authenticated
    USING (
        bucket_id = 'documents'
        AND public.is_tenant_member(
            auth.uid(),
            NULLIF((storage.foldername(name))[1], '')::uuid
        )
    )
    WITH CHECK (
        bucket_id = 'documents'
        AND public.is_tenant_member(
            auth.uid(),
            NULLIF((storage.foldername(name))[1], '')::uuid
        )
    );

CREATE POLICY "documents_tenant_delete"
    ON storage.objects
    FOR DELETE
    TO authenticated
    USING (
        bucket_id = 'documents'
        AND public.is_tenant_member(
            auth.uid(),
            NULLIF((storage.foldername(name))[1], '')::uuid
        )
    );

COMMIT;
