-- =============================================================================
-- Migration 0033: Service Catalogue
-- =============================================================================
-- Introduces a tenant-scoped product/service catalogue for PS firms.
-- 17 system services seeded across 4 practice areas:
--   Accounting (4), Tax (6), Company Secretarial (4), Payroll (3)
--
-- Revenue account codes 4001/4002/4003 are added for Tax, COSEC, Payroll
-- (4000 already exists from migration 0002).
--
-- FKs added (nullable) to:
--   * engagements.service_catalogue_id
--   * invoice_lines.service_catalogue_id
--
-- RLS enforces tenant isolation (same pattern as all other tables).
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- service_catalogue table
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS service_catalogue (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code                text NOT NULL,
    name                text NOT NULL,
    description         text,
    service_line        text NOT NULL CHECK (service_line IN (
                            'accounting', 'tax', 'cosec', 'payroll', 'advisory', 'other'
                        )),
    billing_unit        text NOT NULL DEFAULT 'fixed' CHECK (billing_unit IN (
                            'hour', 'fixed', 'retainer', 'per_employee',
                            'per_entity', 'per_event', 'milestone'
                        )),
    default_rate        numeric(15,2),
    default_currency    text NOT NULL DEFAULT 'GBP',
    revenue_account_id  uuid REFERENCES accounts(id),
    is_active           boolean NOT NULL DEFAULT true,
    is_system           boolean NOT NULL DEFAULT false,
    created_at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, code)
);

ALTER TABLE service_catalogue ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON service_catalogue;
CREATE POLICY tenant_isolation ON service_catalogue
    USING (tenant_id = (current_setting('app.current_tenant_id', true))::uuid);

-- ---------------------------------------------------------------------------
-- FK additions
-- ---------------------------------------------------------------------------

ALTER TABLE engagements
    ADD COLUMN IF NOT EXISTS service_catalogue_id uuid REFERENCES service_catalogue(id);

ALTER TABLE invoice_lines
    ADD COLUMN IF NOT EXISTS service_catalogue_id uuid REFERENCES service_catalogue(id);

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_svc_cat_tenant_line
    ON service_catalogue(tenant_id, service_line)
    WHERE is_active = true;

-- ---------------------------------------------------------------------------
-- Additional revenue accounts: Tax (4001), COSEC (4002), Payroll (4003)
-- Account 4000 (Revenue) already exists from migration 0002.
-- ---------------------------------------------------------------------------

INSERT INTO accounts (tenant_id, code, name, account_type, is_system, parent_id)
SELECT t.id, a.code, a.name, 'revenue', true, NULL
FROM tenants t
CROSS JOIN (VALUES
    ('4001', 'Revenue — Tax Services'),
    ('4002', 'Revenue — Company Secretarial'),
    ('4003', 'Revenue — Payroll')
) AS a(code, name)
ON CONFLICT (tenant_id, code) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Seed 17 system services for all existing tenants
-- ---------------------------------------------------------------------------

INSERT INTO service_catalogue
    (tenant_id, code, name, description, service_line, billing_unit, revenue_account_id, is_system)
SELECT
    t.id,
    svc.code,
    svc.name,
    svc.description,
    svc.service_line,
    svc.billing_unit,
    (SELECT id FROM accounts WHERE tenant_id = t.id AND code = svc.rev_account LIMIT 1),
    true
FROM tenants t
CROSS JOIN (VALUES
    -- Accounting (4)
    ('ACC-001', 'Monthly Management Accounts',
     'Monthly management accounts and commentary',
     'accounting', 'retainer', '4000'),
    ('ACC-002', 'Statutory Annual Accounts',
     'Statutory financial statements preparation and filing',
     'accounting', 'fixed', '4000'),
    ('ACC-003', 'CFO Advisory Services',
     'Part-time CFO and financial advisory (T&M)',
     'accounting', 'hour', '4000'),
    ('ACC-004', 'Group Consolidation',
     'Consolidated group accounts preparation',
     'accounting', 'fixed', '4000'),
    -- Tax (6)
    ('TAX-001', 'Corporation Tax Return (CT600)',
     'Annual corporate tax return preparation and HMRC submission',
     'tax', 'fixed', '4001'),
    ('TAX-002', 'VAT Returns (Quarterly)',
     'Quarterly VAT return preparation and submission',
     'tax', 'retainer', '4001'),
    ('TAX-003', 'Tax Advisory',
     'Ad-hoc tax planning and structuring advice',
     'tax', 'hour', '4001'),
    ('TAX-004', 'Personal Tax Return (SA100)',
     'Self-assessment personal tax return',
     'tax', 'fixed', '4001'),
    ('TAX-005', 'Trust Tax Return',
     'Trust and estate tax compliance',
     'tax', 'fixed', '4001'),
    ('TAX-006', 'CGT Computation',
     'Capital gains tax computation and reporting',
     'tax', 'fixed', '4001'),
    -- Company Secretarial (4)
    ('COS-001', 'Annual Confirmation Statement',
     'Annual confirmation statement filing at Companies House',
     'cosec', 'per_event', '4002'),
    ('COS-002', 'Director Appointment/Resignation',
     'AP01/TM01 filing and register update',
     'cosec', 'per_event', '4002'),
    ('COS-003', 'Share Allotment',
     'SH01 filing and shareholder register update',
     'cosec', 'per_event', '4002'),
    ('COS-004', 'COSEC Retainer',
     'Ongoing company secretarial support and compliance monitoring',
     'cosec', 'retainer', '4002'),
    -- Payroll (3)
    ('PAY-001', 'Monthly Payroll Run',
     'Monthly payroll processing per employee',
     'payroll', 'per_employee', '4003'),
    ('PAY-002', 'Payroll Year-End (P60/P11D)',
     'Year-end payroll reconciliation and statutory returns',
     'payroll', 'fixed', '4003'),
    ('PAY-003', 'RTI Submission',
     'Real-time information filing with HMRC',
     'payroll', 'fixed', '4003')
) AS svc(code, name, description, service_line, billing_unit, rev_account)
ON CONFLICT (tenant_id, code) DO NOTHING;

COMMIT;
