-- =============================================================================
-- Migration 0115: Employee ERP firewall at the RLS layer — batch 1 (issue #466)
--
-- ADR 0005 (D4). The API firewall already rejects the timesheet `employee` role
-- from every ERP `require_role` gate, but RLS did not mirror it: every ERP table
-- policy calls `is_tenant_member`, which is TRUE for ANY active membership incl.
-- a timesheet employee. A portal login could therefore read ERP tables directly
-- via PostgREST, bypassing the API.
--
-- Fix technique — ADDITIVE and reversible: a Postgres RESTRICTIVE policy is AND-ed
-- with the existing (permissive) policies, so we do NOT touch or drop any existing
-- policy. We just add one restrictive layer per ERP table requiring the caller to
-- be a NON-employee member. Employees (role = 'employee') fail it and are blocked;
-- every real ERP role passes it unchanged; the service_role bypasses RLS entirely.
--
-- Batch 1 covers the crown-jewel financial tables. Timesheet/self tables
-- (time_entries, own employees profile) are deliberately EXCLUDED so employees
-- keep their self-service access. Idempotent. Reverse by dropping the policies.
-- =============================================================================

BEGIN;

-- 1. ERP-member helper: active member whose legacy role is not `employee`. -----
CREATE OR REPLACE FUNCTION public.is_tenant_erp_member(
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
           AND lower(coalesce(tu.role, '')) <> 'employee'
    );
$$;

COMMENT ON FUNCTION public.is_tenant_erp_member(UUID, UUID) IS
    'TRUE iff the user is an active tenant member whose legacy role is not the '
    'timesheet `employee` role. Used by RESTRICTIVE ERP-table policies to mirror '
    'the API employee firewall at the RLS layer (#466 / ADR 0005 D4).';

REVOKE ALL ON FUNCTION public.is_tenant_erp_member(UUID, UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.is_tenant_erp_member(UUID, UUID)
    TO authenticated, service_role;

-- 2. Restrictive "erp_member_only" layer on the batch-1 ERP tables. ------------
DO $$
DECLARE
    t TEXT;
    erp_tables TEXT[] := ARRAY[
        'journal_entries',
        'journal_lines',
        'invoices',
        'bills',
        'payments',
        'clients',
        'engagements',
        'projects',
        'bill_payment_batches',
        'bill_payment_items'
    ];
BEGIN
    FOREACH t IN ARRAY erp_tables LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', 'erp_member_only', t);
        EXECUTE format($f$
            CREATE POLICY %I ON public.%I
                AS RESTRICTIVE
                FOR ALL
                TO authenticated
                USING (public.is_tenant_erp_member(auth.uid(), tenant_id))
                WITH CHECK (public.is_tenant_erp_member(auth.uid(), tenant_id))
        $f$, 'erp_member_only', t);
    END LOOP;
END $$;

COMMIT;
