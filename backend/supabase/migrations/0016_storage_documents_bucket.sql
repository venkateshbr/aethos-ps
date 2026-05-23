-- =============================================================================
-- Migration 0016: Storage — `documents` bucket + tenant-isolated RLS policies
-- Issue: #100  (POST /api/v1/documents/upload was 500'ing with
--               `Bucket not found` because the bucket had never been
--               provisioned on the live Supabase project.)
-- Owner:  Sthira (SRE)
-- =============================================================================
--
-- The application uploads files via the service-role client, which bypasses
-- RLS entirely.  Tenant scoping at write time is enforced in the API layer
-- (see `app/api/v1/endpoints/documents.py` — the storage path is constructed
-- from the verified `tenant_id` returned by `get_tenant_id`).  These Storage
-- RLS policies provide **defense in depth** for any future surface that
-- talks to Storage with an `authenticated` JWT (e.g. signed-URL helpers,
-- direct client uploads, or a misconfigured client that picks up the anon
-- key instead of service-role).
--
-- Path convention (must match the API):
--     {tenant_id}/{year}/{month:02d}/{document_id}.{ext}
--
-- The first path segment is the tenant UUID.  `storage.foldername(name)`
-- returns the path as a text[]; index 1 (Postgres arrays are 1-based) is the
-- tenant_id.  We compare that against the JWT subject's active membership
-- rows in `public.tenant_users`.
--
-- Bucket configuration (kept in sync with the API):
--   * private (public = false)
--   * file_size_limit = 20 MiB (20 * 1024 * 1024 = 20971520 bytes)
--   * allowed_mime_types = PDF, JPEG, PNG, WebP, plain text
--
-- This migration is idempotent — it can be re-run safely against any
-- Supabase project (fresh or already partially provisioned).
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Create / refresh the `documents` bucket.
--    storage.buckets is the canonical bucket registry in Supabase Storage.
--    We use ON CONFLICT DO UPDATE so re-runs reconcile config drift.
-- ---------------------------------------------------------------------------

INSERT INTO storage.buckets (
    id,
    name,
    public,
    file_size_limit,
    allowed_mime_types
)
VALUES (
    'documents',
    'documents',
    FALSE,
    20971520,  -- 20 MiB — must match _MAX_FILE_SIZE_BYTES in documents.py
    ARRAY[
        'application/pdf',
        'image/jpeg',
        'image/png',
        'image/webp',
        'text/plain'
    ]
)
ON CONFLICT (id) DO UPDATE
    SET name               = EXCLUDED.name,
        public             = EXCLUDED.public,
        file_size_limit    = EXCLUDED.file_size_limit,
        allowed_mime_types = EXCLUDED.allowed_mime_types;

-- ---------------------------------------------------------------------------
-- 2. RLS on storage.objects — tenant isolation by first path segment.
--    RLS is already enabled on storage.objects by Supabase's bootstrap;
--    we only need to add bucket-scoped policies.
--
--    Helper expression used in every policy:
--      (storage.foldername(name))[1]   -> first path segment (tenant_id, text)
--
--    Membership predicate:
--      EXISTS (
--        SELECT 1 FROM public.tenant_users
--         WHERE user_id    = auth.uid()
--           AND tenant_id  = (storage.foldername(name))[1]::uuid
--           AND deleted_at IS NULL
--      )
--
--    The cast to UUID will raise on a malformed first segment — that is
--    acceptable: the policy then evaluates to NULL/FALSE and the row is
--    denied, which is the safe default.
-- ---------------------------------------------------------------------------

-- Drop any prior versions of these policies so re-running the migration is
-- a clean no-op (idempotency).
DROP POLICY IF EXISTS "documents_tenant_select"  ON storage.objects;
DROP POLICY IF EXISTS "documents_tenant_insert"  ON storage.objects;
DROP POLICY IF EXISTS "documents_tenant_update"  ON storage.objects;
DROP POLICY IF EXISTS "documents_tenant_delete"  ON storage.objects;

-- SELECT — read only files whose first path segment is a tenant you belong to.
CREATE POLICY "documents_tenant_select"
    ON storage.objects
    FOR SELECT
    TO authenticated
    USING (
        bucket_id = 'documents'
        AND EXISTS (
            SELECT 1
              FROM public.tenant_users tu
             WHERE tu.user_id   = auth.uid()
               AND tu.tenant_id = NULLIF((storage.foldername(name))[1], '')::uuid
               AND tu.deleted_at IS NULL
        )
    );

-- INSERT — write only into a path prefixed by a tenant you belong to.
CREATE POLICY "documents_tenant_insert"
    ON storage.objects
    FOR INSERT
    TO authenticated
    WITH CHECK (
        bucket_id = 'documents'
        AND EXISTS (
            SELECT 1
              FROM public.tenant_users tu
             WHERE tu.user_id   = auth.uid()
               AND tu.tenant_id = NULLIF((storage.foldername(name))[1], '')::uuid
               AND tu.deleted_at IS NULL
        )
    );

-- UPDATE — same predicate.  Both USING and WITH CHECK so a row can't be
-- moved out of the tenant prefix.
CREATE POLICY "documents_tenant_update"
    ON storage.objects
    FOR UPDATE
    TO authenticated
    USING (
        bucket_id = 'documents'
        AND EXISTS (
            SELECT 1
              FROM public.tenant_users tu
             WHERE tu.user_id   = auth.uid()
               AND tu.tenant_id = NULLIF((storage.foldername(name))[1], '')::uuid
               AND tu.deleted_at IS NULL
        )
    )
    WITH CHECK (
        bucket_id = 'documents'
        AND EXISTS (
            SELECT 1
              FROM public.tenant_users tu
             WHERE tu.user_id   = auth.uid()
               AND tu.tenant_id = NULLIF((storage.foldername(name))[1], '')::uuid
               AND tu.deleted_at IS NULL
        )
    );

-- DELETE — same predicate.  The API does not yet expose delete; this policy
-- exists so that if/when it does, the right guard is already in place.
CREATE POLICY "documents_tenant_delete"
    ON storage.objects
    FOR DELETE
    TO authenticated
    USING (
        bucket_id = 'documents'
        AND EXISTS (
            SELECT 1
              FROM public.tenant_users tu
             WHERE tu.user_id   = auth.uid()
               AND tu.tenant_id = NULLIF((storage.foldername(name))[1], '')::uuid
               AND tu.deleted_at IS NULL
        )
    );

-- ---------------------------------------------------------------------------
-- Notes for future operators
-- ---------------------------------------------------------------------------
-- * Service-role callers bypass these policies entirely — that is fine, the
--   API layer is where authoritative tenant scoping happens for writes.
-- * If you add a new bucket, copy this migration and adjust:
--     - bucket id/name
--     - file_size_limit + allowed_mime_types
--     - path-segment index if your convention differs
-- * See docs/infra/STORAGE_BUCKETS.md for the operator runbook.
-- ---------------------------------------------------------------------------

COMMIT;
