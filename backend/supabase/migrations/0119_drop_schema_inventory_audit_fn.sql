-- =============================================================================
-- Migration 0119: Drop the temporary schema-inventory audit function
--
-- 0118 added public.schema_inventory_audit() to review migration drift over
-- PostgREST (the prod Postgres port is unreachable from the operator network).
-- The audit is complete — the only real gap was 0109 (applied alongside this).
-- Remove the audit function so it does not linger in prod. Idempotent.
-- =============================================================================

BEGIN;

DROP FUNCTION IF EXISTS public.schema_inventory_audit();

COMMIT;
