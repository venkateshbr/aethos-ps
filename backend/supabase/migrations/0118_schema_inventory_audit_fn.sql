-- =============================================================================
-- Migration 0118: Temporary schema-inventory audit function (drift review)
--
-- The prod Postgres port is not reachable from the operator's network, so this
-- SECURITY DEFINER function exposes the live schema inventory over PostgREST
-- (rpc) for a migration-drift audit. Read-only, returns a single JSONB with the
-- public schema's tables, columns, routines, enum types, indexes, triggers, and
-- policies. Safe to drop after the audit (migration 0119). Idempotent.
-- =============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.schema_inventory_audit()
RETURNS JSONB
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public, pg_catalog
AS $$
    SELECT jsonb_build_object(
        'tables', (
            SELECT coalesce(jsonb_agg(table_name ORDER BY table_name), '[]'::jsonb)
              FROM information_schema.tables
             WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ),
        'columns', (
            SELECT coalesce(jsonb_agg(table_name || '.' || column_name ORDER BY table_name, column_name), '[]'::jsonb)
              FROM information_schema.columns
             WHERE table_schema = 'public'
        ),
        'routines', (
            SELECT coalesce(jsonb_agg(DISTINCT routine_name ORDER BY routine_name), '[]'::jsonb)
              FROM information_schema.routines
             WHERE routine_schema = 'public'
        ),
        'types', (
            SELECT coalesce(jsonb_object_agg(t.typname, e.vals), '{}'::jsonb)
              FROM pg_type t
              JOIN pg_namespace n ON n.oid = t.typnamespace AND n.nspname = 'public'
              JOIN LATERAL (
                  SELECT jsonb_agg(enumlabel ORDER BY enumsortorder) AS vals
                    FROM pg_enum WHERE enumtypid = t.oid
              ) e ON TRUE
             WHERE t.typtype = 'e'
        ),
        'indexes', (
            SELECT coalesce(jsonb_agg(indexname ORDER BY indexname), '[]'::jsonb)
              FROM pg_indexes WHERE schemaname = 'public'
        ),
        'triggers', (
            SELECT coalesce(jsonb_agg(DISTINCT trigger_name ORDER BY trigger_name), '[]'::jsonb)
              FROM information_schema.triggers WHERE trigger_schema = 'public'
        ),
        'policies', (
            SELECT coalesce(jsonb_agg(policyname ORDER BY policyname), '[]'::jsonb)
              FROM pg_policies WHERE schemaname = 'public'
        )
    );
$$;

REVOKE ALL ON FUNCTION public.schema_inventory_audit() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.schema_inventory_audit() TO service_role;

COMMIT;
