-- =============================================================================
-- Migration 0059: Documents Authenticated Read RLS
--
-- Continue service-role reduction for document metadata reads. Upload, delete,
-- extraction, and signed URL generation remain service-role-backed because they
-- write document rows, mutate private storage, or mint storage URLs.
-- =============================================================================

BEGIN;

DROP POLICY IF EXISTS "authenticated_member_read" ON documents;

CREATE POLICY "authenticated_member_read" ON documents
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

COMMIT;
