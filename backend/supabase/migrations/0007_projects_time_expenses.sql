-- =============================================================================
-- Migration 0007: Projects, Assignments, Time Entries, Project Expenses
-- =============================================================================
-- Execution layer under engagements:
--   * project_status enum
--   * projects          — work container with budget and dates
--   * project_assignments — who's on each project (employee × project)
--   * time_entries      — billable hours logged by employee on project
--   * project_expenses  — billable/non-billable project costs (may be receipt-extracted)
--
-- All money: NUMERIC(15,2). All timestamps: TIMESTAMPTZ.
-- Tenant isolation: RLS enforced on every table.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
CREATE TYPE project_status AS ENUM (
    'planning',
    'active',
    'on_hold',
    'completed',
    'cancelled'
);

-- ---------------------------------------------------------------------------
-- projects
-- Work container underneath an engagement.
-- ---------------------------------------------------------------------------
CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    engagement_id   UUID NOT NULL REFERENCES engagements(id) ON DELETE RESTRICT,
    name            TEXT NOT NULL,
    description     TEXT,
    status          project_status NOT NULL DEFAULT 'planning',
    currency        CHAR(3) NOT NULL DEFAULT 'USD',
    -- Monetary budget (e.g. fixed fee portion allocated to this project)
    budget          NUMERIC(15,2),
    -- Hours budget
    budget_hours    NUMERIC(8,2),
    start_date      DATE,
    end_date        DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    CONSTRAINT ck_projects_budget_pos       CHECK (budget IS NULL OR budget >= 0),
    CONSTRAINT ck_projects_budget_hours_pos CHECK (budget_hours IS NULL OR budget_hours >= 0),
    CONSTRAINT ck_projects_dates            CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON projects
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_projects_tenant_id         ON projects(tenant_id)               WHERE deleted_at IS NULL;
CREATE INDEX idx_projects_tenant_engagement ON projects(tenant_id, engagement_id) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- project_assignments
-- Resource allocation: which employee works on which project, in what role.
-- Override rate takes precedence over the rate card for this assignment.
-- ---------------------------------------------------------------------------
CREATE TABLE project_assignments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    employee_id     UUID NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
    role            TEXT,
    -- Inherits project's rate card unless overridden here
    rate_card_id    UUID REFERENCES rate_cards(id) ON DELETE SET NULL,
    -- Explicit per-assignment bill rate override (supersedes rate card)
    override_rate   NUMERIC(15,2),
    start_date      DATE,
    end_date        DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- One employee can only have one active assignment per project
    UNIQUE (project_id, employee_id),
    CONSTRAINT ck_pa_override_rate_pos CHECK (override_rate IS NULL OR override_rate >= 0),
    CONSTRAINT ck_pa_dates CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

ALTER TABLE project_assignments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON project_assignments
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON project_assignments
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_pa_tenant_id   ON project_assignments(tenant_id);
CREATE INDEX idx_pa_project_id  ON project_assignments(project_id);
CREATE INDEX idx_pa_employee_id ON project_assignments(tenant_id, employee_id);

-- ---------------------------------------------------------------------------
-- time_entries
-- Hours logged by an employee on a project for a given date.
-- Hours must be > 0 and <= 24 (validated per-row via CHECK).
-- billing_status: 'unbilled' → 'billed' | 'non_billable'
-- ---------------------------------------------------------------------------
CREATE TABLE time_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    employee_id     UUID NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
    date            DATE NOT NULL,
    hours           NUMERIC(5,2) NOT NULL,
    description     TEXT,
    billable        BOOLEAN NOT NULL DEFAULT TRUE,
    -- Billing lifecycle: unbilled → billed once included on an invoice
    billing_status  TEXT NOT NULL DEFAULT 'unbilled',
    -- Set when an invoice line references this entry
    invoice_id      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    CONSTRAINT ck_te_hours_range        CHECK (hours > 0 AND hours <= 24),
    CONSTRAINT ck_te_billing_status     CHECK (billing_status IN ('unbilled', 'billed', 'non_billable'))
);

ALTER TABLE time_entries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON time_entries
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON time_entries
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_te_tenant_project_date  ON time_entries(tenant_id, project_id, date)   WHERE deleted_at IS NULL;
CREATE INDEX idx_te_tenant_employee_date ON time_entries(tenant_id, employee_id, date)  WHERE deleted_at IS NULL;
CREATE INDEX idx_te_billing_status       ON time_entries(tenant_id, billing_status)     WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- project_expenses
-- Billable or non-billable cost booked to a project.
-- May be extracted from a receipt document by the expense_extractor_agent.
-- ---------------------------------------------------------------------------
CREATE TABLE project_expenses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    -- Employee who incurred the expense (nullable: can be a direct project charge)
    employee_id     UUID REFERENCES employees(id) ON DELETE SET NULL,
    -- Source document (receipt) if agent-extracted
    document_id     UUID REFERENCES documents(id) ON DELETE SET NULL,
    description     TEXT NOT NULL,
    amount          NUMERIC(15,2) NOT NULL,
    currency        CHAR(3) NOT NULL DEFAULT 'USD',
    -- Base-currency equivalent (tenant's base_currency, FX-converted at time of entry)
    base_amount     NUMERIC(15,2),
    fx_rate_id      UUID REFERENCES fx_rates(id) ON DELETE SET NULL,
    expense_date    DATE,
    category        TEXT,
    billable        BOOLEAN NOT NULL DEFAULT TRUE,
    billing_status  TEXT NOT NULL DEFAULT 'unbilled',
    -- Set when an invoice line references this expense
    invoice_id      UUID,
    -- Reimbursement tracking (employee out-of-pocket)
    reimbursable    BOOLEAN NOT NULL DEFAULT FALSE,
    reimbursed_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    CONSTRAINT ck_pe_amount_pos      CHECK (amount > 0),
    CONSTRAINT ck_pe_base_amount_pos CHECK (base_amount IS NULL OR base_amount > 0),
    CONSTRAINT ck_pe_billing_status  CHECK (billing_status IN ('unbilled', 'billed', 'non_billable'))
);

ALTER TABLE project_expenses ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON project_expenses
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON project_expenses
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_pe_tenant_project   ON project_expenses(tenant_id, project_id)      WHERE deleted_at IS NULL;
CREATE INDEX idx_pe_tenant_employee  ON project_expenses(tenant_id, employee_id)     WHERE deleted_at IS NULL AND employee_id IS NOT NULL;
CREATE INDEX idx_pe_billing_status   ON project_expenses(tenant_id, billing_status)  WHERE deleted_at IS NULL;
CREATE INDEX idx_pe_document_id      ON project_expenses(document_id)                WHERE document_id IS NOT NULL;

COMMIT;
