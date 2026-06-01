-- =============================================================================
-- Migration 0021: Timesheet Portal foundations
-- =============================================================================
-- Supports the standalone employee Timesheet Portal + employee master CRUD
-- (issue #134). Additive only — safe to run on an existing pilot database.
--
-- Three concerns:
--   1. Human-readable project / engagement CODES (e.g. PRJ-0001, ENG-0001),
--      generated atomically per-tenant by a DB sequence + BEFORE INSERT trigger
--      (mirrors fn_next_invoice_number in 0008 — never generate codes in app code).
--   2. Timesheet APPROVAL lifecycle on time_entries:
--      draft -> submitted -> approved | rejected, with audit columns.
--      Orthogonal to the existing billing_status (unbilled/billed/non_billable).
--   3. A narrow 'employee' role for portal logins (slotted BELOW viewer in
--      app/core/rbac.py so an employee JWT is rejected by every ERP endpoint).
--
-- All money: NUMERIC(15,2). All timestamps: TIMESTAMPTZ. Tenant isolation via
-- existing RLS — no new policies needed (employees / project_assignments /
-- time_entries already carry tenant_isolation).
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 0. New role enum value.
--    ALTER TYPE ... ADD VALUE runs outside the main txn below and is NOT used
--    in this migration (no rows are written with role='employee' here), which
--    satisfies Postgres' "can't use a new enum value in the same transaction".
-- ---------------------------------------------------------------------------
ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'employee';


BEGIN;

-- ===========================================================================
-- 1. Project / engagement codes
-- ===========================================================================

-- Per-tenant, per-prefix counter. One row per (tenant, prefix).
CREATE TABLE IF NOT EXISTS code_sequences (
    tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    prefix       TEXT NOT NULL,
    last_number  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, prefix)
);

-- Atomically increment + read the next code for a (tenant, prefix).
-- Returns e.g. 'PRJ-0001'. Grows past 4 digits naturally beyond 9999.
CREATE OR REPLACE FUNCTION fn_next_entity_code(p_tenant_id UUID, p_prefix TEXT)
RETURNS TEXT LANGUAGE plpgsql AS $$
DECLARE
    v_next INTEGER;
BEGIN
    INSERT INTO code_sequences (tenant_id, prefix, last_number)
    VALUES (p_tenant_id, p_prefix, 0)
    ON CONFLICT (tenant_id, prefix) DO NOTHING;

    UPDATE code_sequences
       SET last_number = last_number + 1
     WHERE tenant_id = p_tenant_id AND prefix = p_prefix
    RETURNING last_number INTO v_next;

    RETURN p_prefix || '-' || LPAD(v_next::TEXT, 4, '0');
END;
$$;

-- --- projects.code -----------------------------------------------------------
ALTER TABLE projects    ADD COLUMN IF NOT EXISTS code TEXT;
ALTER TABLE engagements ADD COLUMN IF NOT EXISTS code TEXT;

-- Backfill existing rows. fn_next_entity_code is VOLATILE so it is evaluated
-- once per row, yielding unique per-tenant codes and leaving each tenant's
-- counter at its row count so the INSERT triggers continue cleanly from there.
UPDATE engagements SET code = fn_next_entity_code(tenant_id, 'ENG') WHERE code IS NULL;
UPDATE projects    SET code = fn_next_entity_code(tenant_id, 'PRJ') WHERE code IS NULL;

-- Per-tenant uniqueness (only for live rows).
CREATE UNIQUE INDEX IF NOT EXISTS uq_projects_tenant_code
    ON projects (tenant_id, code) WHERE deleted_at IS NULL AND code IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_engagements_tenant_code
    ON engagements (tenant_id, code) WHERE deleted_at IS NULL AND code IS NOT NULL;

-- BEFORE INSERT triggers — assign a code when none was supplied.
CREATE OR REPLACE FUNCTION trg_fn_project_code()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.code IS NULL OR NEW.code = '' THEN
        NEW.code := fn_next_entity_code(NEW.tenant_id, 'PRJ');
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION trg_fn_engagement_code()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.code IS NULL OR NEW.code = '' THEN
        NEW.code := fn_next_entity_code(NEW.tenant_id, 'ENG');
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_project_code ON projects;
CREATE TRIGGER trg_project_code
    BEFORE INSERT ON projects
    FOR EACH ROW EXECUTE FUNCTION trg_fn_project_code();

DROP TRIGGER IF EXISTS trg_engagement_code ON engagements;
CREATE TRIGGER trg_engagement_code
    BEFORE INSERT ON engagements
    FOR EACH ROW EXECUTE FUNCTION trg_fn_engagement_code();

-- ===========================================================================
-- 2. Timesheet approval lifecycle on time_entries
-- ===========================================================================
ALTER TABLE time_entries
    ADD COLUMN IF NOT EXISTS status          TEXT NOT NULL DEFAULT 'draft',
    ADD COLUMN IF NOT EXISTS submitted_at     TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS approved_at      TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS approved_by      UUID,
    ADD COLUMN IF NOT EXISTS rejected_reason  TEXT;

-- Constrain the lifecycle. (Guarded so re-runs don't error.)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_te_status'
    ) THEN
        ALTER TABLE time_entries
            ADD CONSTRAINT ck_te_status
            CHECK (status IN ('draft', 'submitted', 'approved', 'rejected'));
    END IF;
END$$;

-- Existing entries predate the workflow — treat them as already approved so
-- billing keeps working. (New entries default to 'draft'.)
UPDATE time_entries SET status = 'approved' WHERE status = 'draft';

-- Approval-queue lookups: submitted entries by tenant + employee.
CREATE INDEX IF NOT EXISTS idx_te_status
    ON time_entries (tenant_id, status, employee_id) WHERE deleted_at IS NULL;

COMMIT;
