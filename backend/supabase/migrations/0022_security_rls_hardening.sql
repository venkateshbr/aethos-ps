-- 0022_security_rls_hardening.sql
-- Prahari security audit (issue #72) — fix RLS gaps found in 2026-06-12 re-audit.
--
-- FINDING-002: code_sequences has tenant_id but no RLS.
-- FINDING-001: fx_rates is global but writable via anon key without RLS.
-- FINDING-003: procrastinate_* tables are infrastructure with no RLS.

-- code_sequences — tenant-scoped, needs standard isolation policy
ALTER TABLE code_sequences ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON code_sequences
  USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

-- fx_rates — global reference data, read-only for authenticated, write via service-role only
ALTER TABLE fx_rates ENABLE ROW LEVEL SECURITY;
CREATE POLICY fx_rates_read ON fx_rates
  FOR SELECT USING (TRUE);
-- No INSERT/UPDATE/DELETE policy → only service-role can write.

-- procrastinate tables — deny-all for non-service-role (infrastructure only)
DO $$
DECLARE
  tbl TEXT;
BEGIN
  FOR tbl IN
    SELECT tablename FROM pg_tables
    WHERE schemaname = 'public'
      AND tablename LIKE 'procrastinate_%'
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl);
    -- Deny-all restrictive policy — only service-role bypasses RLS.
    EXECUTE format(
      'CREATE POLICY deny_all ON %I AS RESTRICTIVE USING (FALSE)',
      tbl
    );
  END LOOP;
END
$$;
