-- =============================================================================
-- Migration 0096: Dynamics-style security catalog
--
-- Adds system-seeded roles, duties, and privileges while keeping
-- tenant_users.role as the compatibility projection for existing JWT/UI gates.
-- =============================================================================

BEGIN;

ALTER TABLE tenant_users
    ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS security_privileges (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,
    category    TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    is_system   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS security_duties (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code        TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    is_system   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS security_duty_privileges (
    duty_id      UUID NOT NULL REFERENCES security_duties(id) ON DELETE CASCADE,
    privilege_id UUID NOT NULL REFERENCES security_privileges(id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (duty_id, privilege_id)
);

CREATE TABLE IF NOT EXISTS security_roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID REFERENCES tenants(id) ON DELETE CASCADE,
    code        TEXT NOT NULL,
    label       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    legacy_role user_role NOT NULL DEFAULT 'member',
    is_system   BOOLEAN NOT NULL DEFAULT FALSE,
    is_assignable BOOLEAN NOT NULL DEFAULT TRUE,
    rank        INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ,
    CONSTRAINT ck_security_roles_code CHECK (code ~ '^[a-z0-9][a-z0-9_]*$')
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_security_roles_system_code
    ON security_roles (code)
    WHERE tenant_id IS NULL AND deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_security_roles_tenant_code
    ON security_roles (tenant_id, code)
    WHERE tenant_id IS NOT NULL AND deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS security_role_duties (
    role_id    UUID NOT NULL REFERENCES security_roles(id) ON DELETE CASCADE,
    duty_id    UUID NOT NULL REFERENCES security_duties(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (role_id, duty_id)
);

CREATE TABLE IF NOT EXISTS tenant_user_roles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tenant_user_id      UUID NOT NULL REFERENCES tenant_users(id) ON DELETE CASCADE,
    security_role_id    UUID NOT NULL REFERENCES security_roles(id) ON DELETE RESTRICT,
    assigned_by_user_id UUID,
    assigned_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tenant_user_roles_active
    ON tenant_user_roles (tenant_id, tenant_user_id, security_role_id)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_tenant_user_roles_tenant_user
    ON tenant_user_roles (tenant_id, tenant_user_id)
    WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS tenant_user_role_audit_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tenant_user_id      UUID REFERENCES tenant_users(id) ON DELETE SET NULL,
    actor_user_id       UUID,
    action              TEXT NOT NULL CHECK (
        action IN ('assigned', 'removed', 'replaced', 'role_created', 'role_updated', 'role_deactivated')
    ),
    role_code           TEXT,
    previous_role_codes TEXT[] NOT NULL DEFAULT '{}',
    new_role_codes      TEXT[] NOT NULL DEFAULT '{}',
    metadata            JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE security_privileges ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_duties ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_duty_privileges ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_role_duties ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_user_role_audit_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "authenticated_read_system_privileges" ON security_privileges;
CREATE POLICY "authenticated_read_system_privileges" ON security_privileges
    FOR SELECT TO authenticated USING (is_system = TRUE);

DROP POLICY IF EXISTS "authenticated_read_system_duties" ON security_duties;
CREATE POLICY "authenticated_read_system_duties" ON security_duties
    FOR SELECT TO authenticated USING (is_system = TRUE);

DROP POLICY IF EXISTS "authenticated_read_system_duty_privileges" ON security_duty_privileges;
CREATE POLICY "authenticated_read_system_duty_privileges" ON security_duty_privileges
    FOR SELECT TO authenticated USING (TRUE);

DROP POLICY IF EXISTS "authenticated_read_security_roles" ON security_roles;
CREATE POLICY "authenticated_read_security_roles" ON security_roles
    FOR SELECT TO authenticated
    USING (
        tenant_id IS NULL
        OR public.is_tenant_member(auth.uid(), tenant_id)
    );

DROP POLICY IF EXISTS "authenticated_read_security_role_duties" ON security_role_duties;
CREATE POLICY "authenticated_read_security_role_duties" ON security_role_duties
    FOR SELECT TO authenticated USING (TRUE);

DROP POLICY IF EXISTS "tenant_isolation" ON tenant_user_roles;
CREATE POLICY "tenant_isolation" ON tenant_user_roles
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

DROP POLICY IF EXISTS "authenticated_member_read" ON tenant_user_roles;
CREATE POLICY "authenticated_member_read" ON tenant_user_roles
    FOR SELECT TO authenticated
    USING (public.is_tenant_member(auth.uid(), tenant_id));

DROP POLICY IF EXISTS "tenant_isolation" ON tenant_user_role_audit_events;
CREATE POLICY "tenant_isolation" ON tenant_user_role_audit_events
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

DROP TRIGGER IF EXISTS set_updated_at ON security_privileges;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON security_privileges
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();
DROP TRIGGER IF EXISTS set_updated_at ON security_duties;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON security_duties
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();
DROP TRIGGER IF EXISTS set_updated_at ON security_roles;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON security_roles
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

INSERT INTO security_privileges (code, label, category, description)
VALUES
    ('tenant.users.read', 'Read tenant users', 'Security', 'View tenant user membership.'),
    ('tenant.users.manage', 'Manage tenant users', 'Security', 'Create, update, deactivate, and assign tenant users.'),
    ('security.roles.read', 'Read security roles', 'Security', 'View roles, duties, and privileges.'),
    ('security.roles.manage', 'Manage security roles', 'Security', 'Create tenant roles and assign permission sets.'),
    ('settings.read', 'Read settings', 'Settings', 'View tenant settings.'),
    ('settings.manage', 'Manage settings', 'Settings', 'Change tenant configuration.'),
    ('atlas.chat', 'Use Atlas chat', 'AI', 'Use Atlas conversational interface.'),
    ('atlas.tools.read', 'Use read-only Atlas tools', 'AI', 'Ask Atlas to read tenant data.'),
    ('atlas.tools.execute_draft', 'Use draft Atlas tools', 'AI', 'Ask Atlas to prepare draft work.'),
    ('atlas.tools.execute_money_in', 'Use money-in Atlas tools', 'AI', 'Ask Atlas to prepare receivables work.'),
    ('atlas.tools.execute_money_out', 'Use money-out Atlas tools', 'AI', 'Ask Atlas to prepare payables/payment work.'),
    ('clients.read', 'Read clients and vendors', 'O2C/P2P', 'View clients and vendors.'),
    ('clients.manage', 'Manage clients and vendors', 'O2C/P2P', 'Create and update clients and vendors.'),
    ('engagements.read', 'Read engagements', 'O2C', 'View engagements.'),
    ('engagements.manage', 'Manage engagements', 'O2C', 'Create and update engagements.'),
    ('engagements.status_manage', 'Manage engagement status', 'O2C', 'Change engagement status.'),
    ('projects.read', 'Read projects', 'Delivery', 'View projects.'),
    ('projects.manage', 'Manage projects', 'Delivery', 'Create and update projects.'),
    ('employees.read', 'Read people', 'People', 'View employees and resources.'),
    ('employees.manage', 'Manage people', 'People', 'Create and update employee records.'),
    ('employees.invite', 'Invite employees', 'People', 'Create timesheet portal logins.'),
    ('time_entries.read', 'Read time', 'Delivery', 'View time entries.'),
    ('time_entries.create', 'Create time', 'Delivery', 'Log own or permitted time.'),
    ('time_entries.approve', 'Approve time', 'Delivery', 'Approve submitted time.'),
    ('time_entries.manage', 'Manage time', 'Delivery', 'Update team time entries.'),
    ('invoices.read', 'Read invoices', 'O2C', 'View invoices.'),
    ('invoices.draft', 'Draft invoices', 'O2C', 'Create draft invoices.'),
    ('invoices.post', 'Post invoices', 'O2C', 'Post invoice accounting.'),
    ('invoices.send', 'Send invoices', 'O2C', 'Send invoices externally.'),
    ('invoices.mark_paid', 'Mark invoices paid', 'O2C', 'Record invoice payment state.'),
    ('collections.read', 'Read collections', 'O2C', 'View collections work.'),
    ('collections.manage', 'Manage collections', 'O2C', 'Prepare collections actions.'),
    ('collections.send', 'Send collections', 'O2C', 'Send collections communications.'),
    ('bills.read', 'Read bills', 'P2P', 'View vendor bills.'),
    ('bills.manage', 'Manage bills', 'P2P', 'Create and update vendor bills.'),
    ('bills.approve', 'Approve bills', 'P2P', 'Approve bill intake and coding.'),
    ('bill_payments.read', 'Read payment batches', 'P2P', 'View payment batches.'),
    ('bill_payments.prepare', 'Prepare payment batches', 'P2P', 'Prepare payment batches.'),
    ('bill_payments.approve', 'Approve payment batches', 'P2P', 'Approve money-out batches.'),
    ('bill_payments.export', 'Export payment files', 'P2P', 'Export bank files.'),
    ('bill_payments.settle', 'Settle payment batches', 'P2P', 'Mark payment batches settled.'),
    ('procurement.read', 'Read procurement', 'P2P', 'View procurement documents.'),
    ('procurement.manage', 'Manage procurement', 'P2P', 'Create and convert procurement documents.'),
    ('procurement.approve', 'Approve procurement', 'P2P', 'Approve procurement review work.'),
    ('accounting.read', 'Read accounting', 'R2R', 'View journals, accounts, and close state.'),
    ('accounting.journal_prepare', 'Prepare journals', 'R2R', 'Prepare manual journals.'),
    ('accounting.journal_approve', 'Approve journals', 'R2R', 'Approve journal proposals.'),
    ('accounting.journal_post', 'Post journals', 'R2R', 'Post accounting journals.'),
    ('accounting.period_lock', 'Lock periods', 'R2R', 'Lock accounting periods.'),
    ('accounting.period_unlock', 'Unlock periods', 'R2R', 'Unlock accounting periods.'),
    ('accounting.close_manage', 'Manage close', 'R2R', 'Prepare and manage close tasks.'),
    ('accounting.statements_generate', 'Generate statements', 'R2R', 'Generate financial statements.'),
    ('reports.read', 'Read reports', 'Reporting', 'View operational and financial reports.'),
    ('reports.export', 'Export reports', 'Reporting', 'Export reports.'),
    ('documents.read', 'Read documents', 'Documents', 'View tenant documents.'),
    ('documents.upload', 'Upload documents', 'Documents', 'Upload source documents.'),
    ('documents.manage', 'Manage documents', 'Documents', 'Manage document records.'),
    ('inbox.read', 'Read Inbox', 'Controls', 'View human-in-the-loop tasks.'),
    ('inbox.approve_manager', 'Approve manager work', 'Controls', 'Approve manager-threshold work.'),
    ('inbox.approve_admin', 'Approve admin work', 'Controls', 'Approve admin-threshold work.'),
    ('inbox.approve_owner', 'Approve owner work', 'Controls', 'Approve owner-threshold work.'),
    ('agent.autonomy.read', 'Read agent controls', 'AI', 'View agent controls and runs.'),
    ('agent.autonomy.manage', 'Manage agent controls', 'AI', 'Configure agent autonomy and schedules.'),
    ('ai.settings.read', 'Read AI settings', 'AI', 'View AI inference settings.'),
    ('ai.settings.manage', 'Manage AI settings', 'AI', 'Configure AI inference settings.'),
    ('operational_health.read', 'Read operational health', 'Operations', 'View operational health telemetry.'),
    ('integrations.manage', 'Manage integrations', 'Settings', 'Configure integrations.'),
    ('stripe_connect.manage', 'Manage Stripe Connect', 'Settings', 'Configure Stripe Connect.'),
    ('tax_rates.manage', 'Manage tax rates', 'Settings', 'Configure tax rates.'),
    ('service_catalogue.manage', 'Manage service catalogue', 'Settings', 'Configure service catalogue.'),
    ('rate_cards.manage', 'Manage rate cards', 'Settings', 'Configure rate cards.'),
    ('financial_events.read', 'Read financial events', 'Audit', 'View financial event timeline.'),
    ('financial_events.export', 'Export financial events', 'Audit', 'Export audit event data.')
ON CONFLICT (code) DO UPDATE
    SET label = EXCLUDED.label,
        category = EXCLUDED.category,
        description = EXCLUDED.description,
        is_system = TRUE;

INSERT INTO security_duties (code, label, description)
VALUES
    ('tenant_administration', 'Tenant administration', 'Manage tenant-level administration.'),
    ('security_administration', 'Security administration', 'Manage roles, permission sets, and user assignments.'),
    ('finance_read', 'Finance read access', 'Read finance records, reports, documents, and evidence.'),
    ('operations_management', 'Operations management', 'Manage customers, engagements, projects, and operational records.'),
    ('people_time_management', 'People and time management', 'Manage people, timesheets, and time approvals.'),
    ('billing_management', 'Billing management', 'Draft, post, send, and collect invoices.'),
    ('collections_management', 'Collections management', 'Prepare and send collections work.'),
    ('procurement_management', 'Procurement management', 'Create and approve procurement documents.'),
    ('accounts_payable_management', 'Accounts payable management', 'Create, approve, and pay vendor bills.'),
    ('manager_approval', 'Manager-threshold approval', 'Approve manager-threshold Inbox/procurement work.'),
    ('admin_approval', 'Admin-threshold approval', 'Approve admin-threshold money/accounting work.'),
    ('owner_approval', 'Owner-threshold approval', 'Approve owner-threshold work.'),
    ('accounting_management', 'Accounting management', 'Prepare, approve, post journals and manage close.'),
    ('close_management', 'Close management', 'Manage close tasks, period locks, and statements.'),
    ('audit_review', 'Audit review', 'Read audit evidence without mutation authority.'),
    ('ai_operations', 'AI operations', 'Configure AI settings and agent autonomy.'),
    ('employee_timesheet', 'Employee timesheet', 'Use the timesheet portal.')
ON CONFLICT (code) DO UPDATE
    SET label = EXCLUDED.label,
        description = EXCLUDED.description,
        is_system = TRUE;

CREATE TEMP TABLE _rbac_duty_privileges (duty_code TEXT, privilege_code TEXT) ON COMMIT DROP;
INSERT INTO _rbac_duty_privileges VALUES
    ('tenant_administration', 'tenant.users.read'),
    ('tenant_administration', 'tenant.users.manage'),
    ('tenant_administration', 'settings.read'),
    ('tenant_administration', 'settings.manage'),
    ('tenant_administration', 'integrations.manage'),
    ('tenant_administration', 'stripe_connect.manage'),
    ('security_administration', 'security.roles.read'),
    ('security_administration', 'security.roles.manage'),
    ('security_administration', 'tenant.users.read'),
    ('security_administration', 'tenant.users.manage'),
    ('finance_read', 'atlas.chat'),
    ('finance_read', 'atlas.tools.read'),
    ('finance_read', 'clients.read'),
    ('finance_read', 'engagements.read'),
    ('finance_read', 'projects.read'),
    ('finance_read', 'employees.read'),
    ('finance_read', 'time_entries.read'),
    ('finance_read', 'invoices.read'),
    ('finance_read', 'collections.read'),
    ('finance_read', 'bills.read'),
    ('finance_read', 'bill_payments.read'),
    ('finance_read', 'procurement.read'),
    ('finance_read', 'accounting.read'),
    ('finance_read', 'reports.read'),
    ('finance_read', 'documents.read'),
    ('finance_read', 'inbox.read'),
    ('finance_read', 'agent.autonomy.read'),
    ('finance_read', 'ai.settings.read'),
    ('finance_read', 'operational_health.read'),
    ('finance_read', 'financial_events.read'),
    ('operations_management', 'atlas.tools.execute_draft'),
    ('operations_management', 'clients.manage'),
    ('operations_management', 'engagements.manage'),
    ('operations_management', 'projects.manage'),
    ('operations_management', 'documents.upload'),
    ('people_time_management', 'employees.manage'),
    ('people_time_management', 'employees.invite'),
    ('people_time_management', 'time_entries.create'),
    ('people_time_management', 'time_entries.approve'),
    ('people_time_management', 'time_entries.manage'),
    ('billing_management', 'atlas.tools.execute_money_in'),
    ('billing_management', 'invoices.draft'),
    ('billing_management', 'invoices.post'),
    ('billing_management', 'invoices.send'),
    ('billing_management', 'invoices.mark_paid'),
    ('billing_management', 'rate_cards.manage'),
    ('billing_management', 'tax_rates.manage'),
    ('billing_management', 'service_catalogue.manage'),
    ('collections_management', 'collections.manage'),
    ('collections_management', 'collections.send'),
    ('procurement_management', 'procurement.manage'),
    ('procurement_management', 'procurement.approve'),
    ('accounts_payable_management', 'atlas.tools.execute_money_out'),
    ('accounts_payable_management', 'bills.manage'),
    ('accounts_payable_management', 'bills.approve'),
    ('accounts_payable_management', 'bill_payments.prepare'),
    ('accounts_payable_management', 'bill_payments.approve'),
    ('accounts_payable_management', 'bill_payments.export'),
    ('accounts_payable_management', 'bill_payments.settle'),
    ('manager_approval', 'inbox.approve_manager'),
    ('manager_approval', 'procurement.approve'),
    ('admin_approval', 'inbox.approve_admin'),
    ('admin_approval', 'accounting.journal_approve'),
    ('admin_approval', 'bill_payments.approve'),
    ('owner_approval', 'inbox.approve_owner'),
    ('accounting_management', 'accounting.journal_prepare'),
    ('accounting_management', 'accounting.journal_approve'),
    ('accounting_management', 'accounting.journal_post'),
    ('accounting_management', 'accounting.statements_generate'),
    ('close_management', 'accounting.close_manage'),
    ('close_management', 'accounting.period_lock'),
    ('close_management', 'accounting.period_unlock'),
    ('close_management', 'reports.export'),
    ('audit_review', 'financial_events.read'),
    ('audit_review', 'financial_events.export'),
    ('audit_review', 'reports.export'),
    ('ai_operations', 'agent.autonomy.manage'),
    ('ai_operations', 'ai.settings.manage'),
    ('employee_timesheet', 'time_entries.create');

INSERT INTO security_duty_privileges (duty_id, privilege_id)
SELECT d.id, p.id
  FROM _rbac_duty_privileges dp
  JOIN security_duties d ON d.code = dp.duty_code
  JOIN security_privileges p ON p.code = dp.privilege_code
ON CONFLICT DO NOTHING;

INSERT INTO security_roles (tenant_id, code, label, description, legacy_role, is_system, rank)
VALUES
    (NULL, 'tenant_owner', 'Tenant Owner', 'Firm owner with owner-threshold authority and tenant administration.', 'owner', TRUE, 100),
    (NULL, 'tenant_admin', 'Tenant Admin', 'Tenant security and configuration administrator.', 'admin', TRUE, 90),
    (NULL, 'cfo', 'CFO', 'Executive finance owner for performance, cash, controls, and elevated approvals.', 'admin', TRUE, 85),
    (NULL, 'finance_controller', 'Finance Controller', 'Record-to-report owner for close, journals, statements, and accounting controls.', 'admin', TRUE, 80),
    (NULL, 'finance_ops_manager', 'Finance Ops Manager', 'Operational finance manager across O2C, P2P, close readiness, and Inbox work.', 'manager', TRUE, 70),
    (NULL, 'finance_approver', 'Finance Approver', 'Dedicated approval-only reviewer for manager-threshold work.', 'approver', TRUE, 60),
    (NULL, 'finance_operator', 'Finance Operator', 'General finance operator for permitted draft and operational workflows.', 'member', TRUE, 50),
    (NULL, 'procurement_manager', 'Procurement Manager', 'Procurement owner for purchase requests, orders, vendors, and AP matching.', 'manager', TRUE, 65),
    (NULL, 'buyer_requester', 'Buyer / Requester', 'Requester for procurement intake and source evidence.', 'member', TRUE, 45),
    (NULL, 'ap_manager', 'AP Manager', 'Accounts payable owner for bills and payment preparation.', 'manager', TRUE, 65),
    (NULL, 'ap_clerk', 'AP Clerk', 'Accounts payable operator for vendor bills and evidence review.', 'manager', TRUE, 55),
    (NULL, 'ar_manager', 'AR Manager', 'Accounts receivable owner for billing, collections, and receipts.', 'manager', TRUE, 65),
    (NULL, 'billing_specialist', 'Billing Specialist', 'Billing operator for draft invoices and WIP review.', 'manager', TRUE, 55),
    (NULL, 'collections_specialist', 'Collections Specialist', 'Collections operator for reminder preparation and customer follow-up.', 'manager', TRUE, 55),
    (NULL, 'gl_accountant', 'GL Accountant', 'General ledger accountant for journal preparation and review.', 'admin', TRUE, 70),
    (NULL, 'close_manager', 'Close Manager', 'Close owner for blockers, period locks, and statement packages.', 'admin', TRUE, 75),
    (NULL, 'engagement_manager', 'Engagement Manager', 'Delivery/commercial owner for clients, engagements, projects, and WIP.', 'manager', TRUE, 60),
    (NULL, 'resource_manager', 'Resource Manager', 'People and utilization manager for employees, rates, and time approvals.', 'manager', TRUE, 60),
    (NULL, 'auditor', 'Auditor', 'Read-only reviewer for permitted records, reports, and audit evidence.', 'auditor', TRUE, 20),
    (NULL, 'executive_viewer', 'Executive Viewer', 'Read-only executive reviewer for dashboards and reports.', 'viewer', TRUE, 20),
    (NULL, 'ai_ops_admin', 'AI Operations Admin', 'Admin for AI settings, agent autonomy, and operational health.', 'admin', TRUE, 75),
    (NULL, 'timesheet_employee', 'Timesheet Employee', 'Narrow timesheet portal user.', 'employee', TRUE, 10)
ON CONFLICT (code) WHERE tenant_id IS NULL AND deleted_at IS NULL DO UPDATE
    SET label = EXCLUDED.label,
        description = EXCLUDED.description,
        legacy_role = EXCLUDED.legacy_role,
        is_system = TRUE,
        rank = EXCLUDED.rank;

CREATE TEMP TABLE _rbac_role_duties (role_code TEXT, duty_code TEXT) ON COMMIT DROP;
INSERT INTO _rbac_role_duties VALUES
    ('tenant_owner', 'tenant_administration'),
    ('tenant_owner', 'security_administration'),
    ('tenant_owner', 'finance_read'),
    ('tenant_owner', 'operations_management'),
    ('tenant_owner', 'people_time_management'),
    ('tenant_owner', 'billing_management'),
    ('tenant_owner', 'collections_management'),
    ('tenant_owner', 'procurement_management'),
    ('tenant_owner', 'accounts_payable_management'),
    ('tenant_owner', 'manager_approval'),
    ('tenant_owner', 'admin_approval'),
    ('tenant_owner', 'owner_approval'),
    ('tenant_owner', 'accounting_management'),
    ('tenant_owner', 'close_management'),
    ('tenant_owner', 'audit_review'),
    ('tenant_owner', 'ai_operations'),
    ('tenant_admin', 'tenant_administration'),
    ('tenant_admin', 'security_administration'),
    ('tenant_admin', 'finance_read'),
    ('tenant_admin', 'operations_management'),
    ('tenant_admin', 'people_time_management'),
    ('tenant_admin', 'billing_management'),
    ('tenant_admin', 'collections_management'),
    ('tenant_admin', 'procurement_management'),
    ('tenant_admin', 'accounts_payable_management'),
    ('tenant_admin', 'manager_approval'),
    ('tenant_admin', 'admin_approval'),
    ('tenant_admin', 'accounting_management'),
    ('tenant_admin', 'close_management'),
    ('tenant_admin', 'audit_review'),
    ('tenant_admin', 'ai_operations'),
    ('cfo', 'finance_read'),
    ('cfo', 'manager_approval'),
    ('cfo', 'admin_approval'),
    ('cfo', 'audit_review'),
    ('finance_controller', 'finance_read'),
    ('finance_controller', 'billing_management'),
    ('finance_controller', 'accounts_payable_management'),
    ('finance_controller', 'manager_approval'),
    ('finance_controller', 'admin_approval'),
    ('finance_controller', 'accounting_management'),
    ('finance_controller', 'close_management'),
    ('finance_controller', 'audit_review'),
    ('finance_ops_manager', 'finance_read'),
    ('finance_ops_manager', 'operations_management'),
    ('finance_ops_manager', 'people_time_management'),
    ('finance_ops_manager', 'billing_management'),
    ('finance_ops_manager', 'collections_management'),
    ('finance_ops_manager', 'procurement_management'),
    ('finance_ops_manager', 'accounts_payable_management'),
    ('finance_ops_manager', 'manager_approval'),
    ('finance_approver', 'finance_read'),
    ('finance_approver', 'manager_approval'),
    ('finance_operator', 'finance_read'),
    ('finance_operator', 'operations_management'),
    ('procurement_manager', 'finance_read'),
    ('procurement_manager', 'procurement_management'),
    ('procurement_manager', 'accounts_payable_management'),
    ('procurement_manager', 'manager_approval'),
    ('buyer_requester', 'finance_read'),
    ('buyer_requester', 'procurement_management'),
    ('ap_manager', 'finance_read'),
    ('ap_manager', 'accounts_payable_management'),
    ('ap_manager', 'manager_approval'),
    ('ap_clerk', 'finance_read'),
    ('ap_clerk', 'accounts_payable_management'),
    ('ar_manager', 'finance_read'),
    ('ar_manager', 'billing_management'),
    ('ar_manager', 'collections_management'),
    ('ar_manager', 'manager_approval'),
    ('billing_specialist', 'finance_read'),
    ('billing_specialist', 'billing_management'),
    ('collections_specialist', 'finance_read'),
    ('collections_specialist', 'collections_management'),
    ('gl_accountant', 'finance_read'),
    ('gl_accountant', 'accounting_management'),
    ('gl_accountant', 'manager_approval'),
    ('close_manager', 'finance_read'),
    ('close_manager', 'accounting_management'),
    ('close_manager', 'close_management'),
    ('close_manager', 'manager_approval'),
    ('close_manager', 'admin_approval'),
    ('engagement_manager', 'finance_read'),
    ('engagement_manager', 'operations_management'),
    ('engagement_manager', 'people_time_management'),
    ('engagement_manager', 'billing_management'),
    ('resource_manager', 'finance_read'),
    ('resource_manager', 'people_time_management'),
    ('auditor', 'finance_read'),
    ('auditor', 'audit_review'),
    ('executive_viewer', 'finance_read'),
    ('ai_ops_admin', 'finance_read'),
    ('ai_ops_admin', 'ai_operations'),
    ('timesheet_employee', 'employee_timesheet');

INSERT INTO security_role_duties (role_id, duty_id)
SELECT r.id, d.id
  FROM _rbac_role_duties rd
  JOIN security_roles r ON r.code = rd.role_code AND r.tenant_id IS NULL AND r.deleted_at IS NULL
  JOIN security_duties d ON d.code = rd.duty_code
ON CONFLICT DO NOTHING;

INSERT INTO tenant_user_roles (tenant_id, tenant_user_id, security_role_id)
SELECT tu.tenant_id,
       tu.id,
       sr.id
  FROM tenant_users tu
  JOIN security_roles sr
    ON sr.tenant_id IS NULL
   AND sr.deleted_at IS NULL
   AND sr.code = CASE tu.role::TEXT
        WHEN 'owner' THEN 'tenant_owner'
        WHEN 'admin' THEN 'tenant_admin'
        WHEN 'manager' THEN 'finance_ops_manager'
        WHEN 'approver' THEN 'finance_approver'
        WHEN 'member' THEN 'finance_operator'
        WHEN 'auditor' THEN 'auditor'
        WHEN 'viewer' THEN 'executive_viewer'
        WHEN 'employee' THEN 'timesheet_employee'
        ELSE 'executive_viewer'
   END
 WHERE tu.deleted_at IS NULL
ON CONFLICT DO NOTHING;

DROP VIEW IF EXISTS tenant_user_effective_privileges;
CREATE VIEW tenant_user_effective_privileges AS
SELECT tu.tenant_id,
       tu.user_id,
       tu.id AS tenant_user_id,
       sr.code AS role_code,
       sr.label AS role_label,
       sr.legacy_role::TEXT AS legacy_role,
       sp.code AS privilege_code,
       sp.label AS privilege_label,
       sp.category AS privilege_category
  FROM tenant_users tu
  JOIN tenant_user_roles tur
    ON tur.tenant_id = tu.tenant_id
   AND tur.tenant_user_id = tu.id
   AND tur.deleted_at IS NULL
  JOIN security_roles sr
    ON sr.id = tur.security_role_id
   AND sr.deleted_at IS NULL
   AND (sr.tenant_id IS NULL OR sr.tenant_id = tu.tenant_id)
  JOIN security_role_duties srd ON srd.role_id = sr.id
  JOIN security_duty_privileges sdp ON sdp.duty_id = srd.duty_id
  JOIN security_privileges sp ON sp.id = sdp.privilege_id
 WHERE tu.deleted_at IS NULL;

COMMENT ON TABLE security_privileges IS
    'System master list of atomic privileges used by the enterprise RBAC resolver.';
COMMENT ON TABLE security_duties IS
    'System master list of duties, each bundling related privileges.';
COMMENT ON TABLE security_roles IS
    'System and tenant roles, Dynamics-style, projected to legacy tenant_users.role during transition.';
COMMENT ON TABLE tenant_user_roles IS
    'Tenant user to security role assignments.';
COMMENT ON COLUMN tenant_users.must_change_password IS
    'True when an admin-created user must change the initial password before normal app use.';

COMMIT;
