-- =============================================================================
-- Migration 0116: Employee ERP firewall at the RLS layer — batch 2 (issue #466)
--
-- Extends the batch-1 firewall (0115) to the remaining tenant-scoped ERP tables,
-- so a timesheet `employee` login cannot read them via direct PostgREST. Same
-- ADDITIVE, reversible RESTRICTIVE-policy technique (AND-ed with existing
-- policies; no existing policy touched; service_role bypasses RLS).
--
-- Two shapes:
--   * erp_member_only        — pure ERP tables employees must never read.
--   * erp_member_or_self     — `employees`: ERP members see all; an employee sees
--                              ONLY their own row (user_id = auth.uid()).
--
-- time_entries stays fully excluded (employee self-service, handled by its own
-- policies). Each table is guarded by to_regclass so a name absent in some
-- environment is skipped rather than failing the whole migration. Idempotent.
-- =============================================================================

BEGIN;

-- 1. Pure ERP tables — employees blocked entirely. ----------------------------
DO $$
DECLARE
    t TEXT;
    erp_tables TEXT[] := ARRAY[
        'invoice_lines',
        'bill_lines',
        'tax_rates',
        'rate_cards',
        'service_catalogue',
        'project_expenses',
        'documents',
        'agent_suggestions',
        'hitl_tasks',
        'agent_runs',
        'agent_workflow_runs',
        'financial_events',
        'period_locks',
        'revenue_recognition_schedules',
        'client_groups'
    ];
BEGIN
    FOREACH t IN ARRAY erp_tables LOOP
        IF to_regclass('public.' || t) IS NULL THEN
            RAISE NOTICE 'skip %, table not present', t;
            CONTINUE;
        END IF;
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

-- 2. employees — ERP members see all; an employee sees only their own row. -----
DO $$
BEGIN
    IF to_regclass('public.employees') IS NOT NULL THEN
        DROP POLICY IF EXISTS "erp_member_or_self" ON public.employees;
        CREATE POLICY "erp_member_or_self" ON public.employees
            AS RESTRICTIVE
            FOR ALL
            TO authenticated
            USING (
                public.is_tenant_erp_member(auth.uid(), tenant_id)
                OR user_id = auth.uid()
            )
            WITH CHECK (
                public.is_tenant_erp_member(auth.uid(), tenant_id)
                OR user_id = auth.uid()
            );
    END IF;
END $$;

COMMIT;
