/**
 * Enterprise finance persona matrix proof for #321.
 *
 * The product currently maps named finance personas onto the enforced tenant
 * role hierarchy. This spec proves the browser-visible compatibility matrix
 * and the key route/action affordances for every named persona.
 */

import { expect, Locator, Page, test } from '@playwright/test';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'http://localhost:4201';

type MockRole = 'owner' | 'admin' | 'manager' | 'approver' | 'auditor' | 'viewer';

interface PersonaCase {
  persona: string;
  role: MockRole;
  compatiblePersonas: string[];
  settingsCanEdit: boolean;
  canCreateAp: boolean;
  canAccessPayBills: boolean;
  canDraftInvoice: boolean;
  canPostInvoice: boolean;
  canPostJournal: boolean;
  canRunClose: boolean;
  readOnly: boolean;
}

const approvalPolicy = {
  tenant_id: 'tenant-persona',
  policy_source: 'tenant_default',
  money_out_default_role: 'owner',
  money_out_owner_threshold: '25000',
  money_out_owner_role: 'owner',
  accounting_role: 'admin',
  money_in_role: 'manager',
  draft_role: 'manager',
  external_send_role: 'admin',
  high_risk_role: 'owner',
  created_at: '2026-06-25T02:00:00Z',
  updated_at: '2026-06-25T02:00:00Z',
};

const personas = [
  {
    id: 'owner_admin',
    label: 'Owner/Admin',
    mapped_roles: ['owner', 'admin'],
    description: 'Tenant and finance operations administrator.',
    areas: ['Settings', 'Approval policy', 'Agent controls', 'Final approvals'],
    allowed_actions: ['Configure tenant controls and AI operations'],
    restricted_actions: ['Tenant-scoped only'],
    read_only: false,
  },
  {
    id: 'controller',
    label: 'Controller',
    mapped_roles: ['admin', 'owner'],
    description: 'Record-to-report owner for close, journals, and statements.',
    areas: ['Accounting', 'Close', 'Reports', 'Audit'],
    allowed_actions: ['Post and review journals through guarded accounting flows'],
    restricted_actions: ['Cannot bypass owner-threshold policy or tenant boundaries'],
    read_only: false,
  },
  {
    id: 'finance_approver',
    label: 'Finance Approver',
    mapped_roles: ['approver', 'manager', 'admin', 'owner'],
    description: 'Dedicated reviewer for manager-threshold Inbox decisions.',
    areas: ['Inbox', 'Approval controls', 'Decision evidence'],
    allowed_actions: ['Approve manager-threshold review work'],
    restricted_actions: ['Cannot create or mutate operational records outside review actions'],
    read_only: false,
  },
  {
    id: 'procurement_manager',
    label: 'Procurement Manager',
    mapped_roles: ['manager', 'admin', 'owner'],
    description: 'Procurement owner for purchase requests, orders, vendors, and AP matching.',
    areas: ['Procurement', 'Bills', 'Pay Bills', 'Vendor onboarding'],
    allowed_actions: ['Create and convert procurement documents'],
    restricted_actions: ['Cannot approve admin or owner-threshold spend unless mapped to admin/owner'],
    read_only: false,
  },
  {
    id: 'ap_lead',
    label: 'AP Lead',
    mapped_roles: ['manager', 'admin', 'owner'],
    description: 'Procure-to-pay operator for vendors, bills, and payment preparation.',
    areas: ['Bills', 'Procurement', 'Pay Bills', 'AP Aging'],
    allowed_actions: ['Create and review bills and procurement documents'],
    restricted_actions: ['Cannot approve admin or owner-threshold money-out work'],
    read_only: false,
  },
  {
    id: 'ar_lead',
    label: 'AR Lead',
    mapped_roles: ['manager', 'admin', 'owner'],
    description: 'Order-to-cash operator for invoices, collections, and receipts.',
    areas: ['Invoices', 'Collections', 'Reports', 'Inbox'],
    allowed_actions: ['Draft and review invoices'],
    restricted_actions: ['Cannot bypass send, payment, or admin-threshold approval gates'],
    read_only: false,
  },
  {
    id: 'auditor',
    label: 'Auditor',
    mapped_roles: ['auditor'],
    description: 'Read-only audit reviewer for records, reports, and decision evidence.',
    areas: ['Reports', 'Bills', 'Invoices', 'Audit evidence'],
    allowed_actions: ['Inspect permitted tenant records and record-scoped decision timelines'],
    restricted_actions: ['Cannot create, approve, edit, reject, post, pay, send, lock, or change settings'],
    read_only: true,
  },
  {
    id: 'executive',
    label: 'Executive',
    mapped_roles: ['viewer'],
    description: 'Read-only leader reviewing operational and financial status.',
    areas: ['Reports', 'Management cockpit', 'Action queues'],
    allowed_actions: ['Inspect dashboards, reports, record details, and status evidence'],
    restricted_actions: ['Cannot create, approve, edit, reject, post, pay, send, lock, or change settings'],
    read_only: true,
  },
];

const personaCases: PersonaCase[] = [
  {
    persona: 'Owner/Admin',
    role: 'owner',
    compatiblePersonas: ['Owner/Admin', 'Controller', 'Finance Approver', 'Procurement Manager', 'AP Lead', 'AR Lead'],
    settingsCanEdit: true,
    canCreateAp: true,
    canAccessPayBills: true,
    canDraftInvoice: true,
    canPostInvoice: true,
    canPostJournal: true,
    canRunClose: true,
    readOnly: false,
  },
  {
    persona: 'Controller',
    role: 'admin',
    compatiblePersonas: ['Owner/Admin', 'Controller', 'Finance Approver', 'Procurement Manager', 'AP Lead', 'AR Lead'],
    settingsCanEdit: true,
    canCreateAp: true,
    canAccessPayBills: true,
    canDraftInvoice: true,
    canPostInvoice: true,
    canPostJournal: true,
    canRunClose: true,
    readOnly: false,
  },
  {
    persona: 'AP Lead',
    role: 'manager',
    compatiblePersonas: ['Finance Approver', 'Procurement Manager', 'AP Lead', 'AR Lead'],
    settingsCanEdit: false,
    canCreateAp: true,
    canAccessPayBills: true,
    canDraftInvoice: true,
    canPostInvoice: true,
    canPostJournal: true,
    canRunClose: false,
    readOnly: false,
  },
  {
    persona: 'AR Lead',
    role: 'manager',
    compatiblePersonas: ['Finance Approver', 'Procurement Manager', 'AP Lead', 'AR Lead'],
    settingsCanEdit: false,
    canCreateAp: true,
    canAccessPayBills: true,
    canDraftInvoice: true,
    canPostInvoice: true,
    canPostJournal: true,
    canRunClose: false,
    readOnly: false,
  },
  {
    persona: 'Finance Approver',
    role: 'approver',
    compatiblePersonas: ['Finance Approver'],
    settingsCanEdit: false,
    canCreateAp: false,
    canAccessPayBills: true,
    canDraftInvoice: false,
    canPostInvoice: false,
    canPostJournal: false,
    canRunClose: false,
    readOnly: false,
  },
  {
    persona: 'Auditor',
    role: 'auditor',
    compatiblePersonas: ['Auditor'],
    settingsCanEdit: false,
    canCreateAp: false,
    canAccessPayBills: true,
    canDraftInvoice: false,
    canPostInvoice: false,
    canPostJournal: false,
    canRunClose: false,
    readOnly: true,
  },
  {
    persona: 'Executive',
    role: 'viewer',
    compatiblePersonas: ['Executive'],
    settingsCanEdit: false,
    canCreateAp: false,
    canAccessPayBills: true,
    canDraftInvoice: false,
    canPostInvoice: false,
    canPostJournal: false,
    canRunClose: false,
    readOnly: true,
  },
];

const invoiceRows = [
  {
    id: 'inv-draft',
    invoice_number: 'INV-PER-001',
    client_name: 'Persona Matrix Client',
    status: 'draft',
    currency: 'USD',
    total_amount: '1200.00',
    issue_date: '2026-06-20',
    due_date: '2026-07-20',
  },
  {
    id: 'inv-approved',
    invoice_number: 'INV-PER-002',
    client_name: 'Persona Matrix Client',
    status: 'approved',
    currency: 'USD',
    total_amount: '2400.00',
    issue_date: '2026-06-21',
    due_date: '2026-07-21',
  },
];

const billRows = [
  {
    id: 'bill-persona',
    bill_number: 'BILL-PER-001',
    vendor_name: 'Persona Vendor',
    issue_date: '2026-06-20',
    due_date: '2026-07-20',
    amount: '900.00',
    total: '900.00',
    currency: 'USD',
    status: 'approved',
    po_match_status: 'matched',
    po_match_summary: {},
  },
];

const inboxTasks = [
  {
    id: 'task-owner-pay',
    tenant_id: 'tenant-persona',
    kind: 'create_bill_payment_batch',
    priority: 'high',
    title: 'Review owner-threshold payment batch',
    agent_name: 'finance_ops_manager',
    confidence: '0.91',
    status: 'open',
    created_at: '2026-06-25T02:00:00Z',
    suggestion_payload: {
      total_amount: '75000.00',
      currency: 'USD',
    },
    required_approval_role: 'owner',
    approval_policy_reason: 'money_out_above_owner_review_threshold',
  },
];

interface MockCatalogPermissions {
  roleCode: string;
  roleLabel: string;
  privilegeCodes: string[];
}

const financeOpsSurfacePrivileges = [
  'procurement.manage',
  'bills.manage',
  'bill_payments.read',
  'invoices.draft',
  'invoices.post',
  'invoices.send',
  'invoices.mark_paid',
];

/** Catalog privileges consumed by the browser surfaces exercised in this matrix. */
const catalogPermissionsByRole: Record<MockRole, MockCatalogPermissions> = {
  owner: {
    roleCode: 'tenant_owner',
    roleLabel: 'Tenant Owner',
    privilegeCodes: financeOpsSurfacePrivileges,
  },
  admin: {
    roleCode: 'tenant_admin',
    roleLabel: 'Tenant Admin',
    privilegeCodes: financeOpsSurfacePrivileges,
  },
  manager: {
    roleCode: 'finance_ops_manager',
    roleLabel: 'Finance Ops Manager',
    privilegeCodes: financeOpsSurfacePrivileges,
  },
  approver: {
    roleCode: 'finance_approver',
    roleLabel: 'Finance Approver',
    privilegeCodes: ['procurement.approve', 'bill_payments.read'],
  },
  auditor: {
    roleCode: 'auditor',
    roleLabel: 'Auditor',
    privilegeCodes: ['bill_payments.read'],
  },
  viewer: {
    roleCode: 'executive_viewer',
    roleLabel: 'Executive Viewer',
    privilegeCodes: ['bill_payments.read'],
  },
};

const zeroAging = {
  '0_30': '0.00',
  '31_60': '0.00',
  '61_90': '0.00',
  over_90: '0.00',
  total: '0.00',
};

const trialBalance = {
  as_of_period: '2026-06',
  lines: [],
  grand_total_dr: '0.00',
  grand_total_cr: '0.00',
  is_balanced: true,
  generated_at: '2026-06-25T02:00:00Z',
};

const balanceSheet = {
  as_of_period: '2026-06',
  asset_lines: [],
  liability_lines: [],
  equity_lines: [],
  total_assets: '0.00',
  total_liabilities: '0.00',
  total_equity: '0.00',
  liabilities_and_equity: '0.00',
  is_balanced: true,
  generated_at: '2026-06-25T02:00:00Z',
};

const retainedEarnings = {
  period: '2026-06',
  previous_period: '2026-05',
  beginning_retained_earnings: '0.00',
  current_period_net_income: '0.00',
  retained_earnings_activity: '0.00',
  ending_retained_earnings: '0.00',
  generated_at: '2026-06-25T02:00:00Z',
};

const incomeStatement = {
  period_start: '2026-06',
  period_end: '2026-06',
  revenue_lines: [],
  expense_lines: [],
  total_revenue: '0.00',
  total_expenses: '0.00',
  net_income: '0.00',
  generated_at: '2026-06-25T02:00:00Z',
};

const cashFlow = {
  period_start: '2026-06',
  period_end: '2026-06',
  operating_lines: [],
  investing_lines: [],
  financing_lines: [],
  net_cash_from_operating: '0.00',
  net_cash_from_investing: '0.00',
  net_cash_from_financing: '0.00',
  net_change_in_cash: '0.00',
  beginning_cash: '0.00',
  ending_cash: '0.00',
  generated_at: '2026-06-25T02:00:00Z',
};

const statutoryPack = {
  period_start: '2026-06',
  period_end: '2026-06',
  as_of_period: '2026-06',
  country: 'US',
  market: 'United States',
  base_currency: 'USD',
  locale: 'en-US',
  timezone: 'America/New_York',
  tax_label: 'Sales Tax',
  tax_authority_label: 'State tax authority',
  tax_collection_model: 'sales_tax',
  reporting_periods: ['2026-06'],
  trial_balance: trialBalance,
  balance_sheet: balanceSheet,
  income_statement: incomeStatement,
  cash_flow: cashFlow,
  retained_earnings_roll_forward: retainedEarnings,
  tax_summary: {
    tax_label: 'Sales Tax',
    tax_authority_label: 'State tax authority',
    base_currency: 'USD',
    transaction_currency_buckets: [],
    ledger_output_tax_payable_balance: '0.00',
    ledger_input_tax_recoverable_balance: '0.00',
    ledger_net_tax_payable: '0.00',
  },
  generated_at: '2026-06-25T02:00:00Z',
};

async function authenticate(page: Page, role: MockRole): Promise<void> {
  await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' });
  await page.evaluate(({ currentRole }) => {
    window.localStorage.setItem('aethos_token', `mock-token-${currentRole}`);
    window.localStorage.setItem('aethos_tenant_id', 'tenant-persona');
    window.localStorage.setItem('aethos_role', currentRole);
  }, { currentRole: role });
}

async function installPersonaMocks(page: Page, role: MockRole): Promise<void> {
  const permissions = catalogPermissionsByRole[role];
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (request.method() !== 'GET') {
      await route.fulfill({ status: 403, json: { detail: 'Mocked RBAC denial for persona matrix proof' } });
      return;
    }

    if (path === '/api/v1/security/me/permissions') {
      await route.fulfill({
        json: {
          tenant_id: 'tenant-persona',
          user_id: `user-${role}`,
          legacy_role: role,
          role_codes: [permissions.roleCode],
          role_labels: [permissions.roleLabel],
          privilege_codes: permissions.privilegeCodes,
          must_change_password: false,
        },
      });
      return;
    }

    if (path.endsWith('/approval-policy/effective')) {
      await route.fulfill({ json: approvalPolicy });
      return;
    }
    if (path.endsWith('/tenants/finance-personas')) {
      await route.fulfill({ json: { items: personas } });
      return;
    }
    if (path.endsWith('/agents/finance-ops/schedule')) {
      await route.fulfill({
        json: {
          enabled: true,
          cadence: 'daily',
          run_hour_utc: 7,
          run_day_of_week: null,
          period_mode: 'current_month',
          max_work_items: 5,
          stale_after_hours: 24,
          high_risk_stale_after_hours: 4,
          escalation_enabled: true,
          updated_at: '2026-06-25T02:00:00Z',
          last_run_at: null,
        },
      });
      return;
    }
    if (path.endsWith('/tenants/health')) {
      await route.fulfill({
        json: {
          status: 'ok',
          generated_at: '2026-06-25T02:00:00Z',
          runtime: { environment: 'test', debug: false, queue_configured: true, queue_required: false, extraction_mode: 'sync' },
          rate_limit: { enabled: true, backend: 'memory', distributed_configured: false, fallback_to_memory: true, window_seconds: 60 },
          checks: { tables: [] },
          telemetry: {
            request_failures: [],
            background_failures: [],
            failed_agent_runs_24h: 0,
            failed_tool_invocations_24h: 0,
            failed_workflow_runs_24h: 0,
            failed_tools_by_name_24h: [],
            window_start: '2026-06-25T00:00:00Z',
          },
          alerts: { route: { route_type: 'runbook_queue', channel: 'runbook', configured: false }, items: [] },
        },
      });
      return;
    }
    if (path.endsWith('/inbox/tasks')) {
      await route.fulfill({ json: { items: inboxTasks, total: inboxTasks.length } });
      return;
    }
    if (path.endsWith('/bills')) {
      await route.fulfill({ json: { items: billRows, total: billRows.length } });
      return;
    }
    if (path.endsWith('/procurement/documents')) {
      await route.fulfill({ json: { items: [], total: 0 } });
      return;
    }
    if (path.endsWith('/invoices')) {
      await route.fulfill({ json: invoiceRows });
      return;
    }
    if (path.endsWith('/accounting/journal-entries')) {
      await route.fulfill({ json: { items: [], total: 0 } });
      return;
    }
    if (path.includes('/accounting/periods/') && path.endsWith('/close-tasks')) {
      await route.fulfill({ json: { tasks: [] } });
      return;
    }
    if (path.endsWith('/accounting/recurring-journal-templates')) {
      await route.fulfill({ json: { templates: [] } });
      return;
    }
    if (path.endsWith('/accounts')) {
      await route.fulfill({ json: [{ id: 'acct-cash', code: '1000', name: 'Cash' }] });
      return;
    }
    if (path.endsWith('/reports/ar-aging') || path.endsWith('/reports/ap-aging')) {
      await route.fulfill({ json: zeroAging });
      return;
    }
    if (path.endsWith('/reports/trial-balance')) {
      await route.fulfill({ json: trialBalance });
      return;
    }
    if (path.endsWith('/reports/balance-sheet')) {
      await route.fulfill({ json: balanceSheet });
      return;
    }
    if (path.endsWith('/reports/retained-earnings-roll-forward')) {
      await route.fulfill({ json: retainedEarnings });
      return;
    }
    if (path.endsWith('/reports/income-statement')) {
      await route.fulfill({ json: incomeStatement });
      return;
    }
    if (path.endsWith('/reports/cash-flow')) {
      await route.fulfill({ json: cashFlow });
      return;
    }
    if (path.endsWith('/reports/statutory-pack')) {
      await route.fulfill({ json: statutoryPack });
      return;
    }
    if (path.startsWith('/api/v1/reports/')) {
      await route.fulfill({ json: [] });
      return;
    }
    if (path.endsWith('/tax-rates')) {
      await route.fulfill({ json: [] });
      return;
    }
    if (path.endsWith('/services')) {
      await route.fulfill({ json: { items: [] } });
      return;
    }
    if (path.endsWith('/integrations/catalog')) {
      await route.fulfill({ json: { integrations: [], total: 0 } });
      return;
    }
    if (path.endsWith('/stripe/connect/status')) {
      await route.fulfill({ json: { connected: false } });
      return;
    }
    if (path.endsWith('/collections/policies/effective')) {
      await route.fulfill({
        json: {
          tenant_id: 'tenant-persona',
          policy_source: 'system_default',
          gentle_after_days: 7,
          firm_after_days: 30,
          pause_after_reminder_count: 3,
          updated_at: null,
        },
      });
      return;
    }
    if (path.endsWith('/agents/runs') || path.endsWith('/agents/workflow-runs')) {
      await route.fulfill({ json: { items: [], total: 0 } });
      return;
    }
    if (path.endsWith('/agents/autonomy-status')) {
      await route.fulfill({ json: { agents: [] } });
      return;
    }

    await route.fulfill({ json: { items: [], total: 0 } });
  });
}

async function expectSettingsMatrix(page: Page, personaCase: PersonaCase): Promise<void> {
  await page.goto(`${BASE}/app/settings`, { waitUntil: 'domcontentloaded' });

  await expect(page.getByRole('heading', { name: 'Finance role personas' })).toBeVisible();
  await expect(
    page.getByText('Current enforced role').locator('..').locator('p.text-sm.font-medium'),
  ).toHaveText(roleLabel(personaCase.role));

  for (const persona of personas) {
    await expect(page.getByRole('heading', { name: persona.label })).toBeVisible();
  }
  for (const label of personaCase.compatiblePersonas) {
    await expect(
      page.getByText('Current enforced role').locator('..').locator('span').getByText(label, { exact: true }),
    ).toBeVisible();
  }

  const saveButton = page.getByLabel('Approval Controls').getByRole('button', { name: /Save Policy/i });
  if (personaCase.settingsCanEdit) {
    await expect(saveButton).toBeEnabled();
  } else {
    await expect(saveButton).toBeDisabled();
    await expect(page.getByText('Approval policy changes require Admin or Owner.')).toBeVisible();
  }
}

async function expectInboxPolicy(page: Page, personaCase: PersonaCase): Promise<void> {
  await page.goto(`${BASE}/app/inbox`, { waitUntil: 'domcontentloaded' });

  const card = page.getByRole('article', { name: 'Review owner-threshold payment batch' });
  await expect(card).toBeVisible();
  await expect(card.getByText('Owner approval')).toBeVisible();

  const approveButton = card.getByRole('button', {
    name: personaCase.role === 'owner'
      ? /Approve Review owner-threshold payment batch/i
      : /Approval requires Owner/i,
  });
  if (personaCase.role === 'owner') {
    await expect(approveButton).toBeEnabled();
  } else {
    await expect(approveButton).toBeDisabled();
  }
}

async function expectBillsControls(page: Page, personaCase: PersonaCase): Promise<void> {
  await page.goto(`${BASE}/app/bills`, { waitUntil: 'domcontentloaded' });

  await expect(page.getByRole('heading', { name: 'Bills' })).toBeVisible();
  await expectControl(page.getByLabel('Create new purchase order or service order'), personaCase.canCreateAp);
  await expectControl(page.getByLabel('Create new bill'), personaCase.canCreateAp);
  await expectControl(page.getByLabel('Go to Pay Bills wizard'), personaCase.canAccessPayBills);
}

async function expectInvoiceControls(page: Page, personaCase: PersonaCase): Promise<void> {
  await page.goto(`${BASE}/app/invoices`, { waitUntil: 'domcontentloaded' });

  await expect(page.getByRole('heading', { name: 'Invoices' })).toBeVisible();
  await expectControl(page.getByLabel(/Create new invoice/), personaCase.canDraftInvoice);
  await expectControl(page.getByLabel('Approve invoice INV-PER-001'), personaCase.canPostInvoice);
  await expectControl(page.getByLabel('Send invoice INV-PER-002'), personaCase.canPostInvoice);
  await expectControl(page.getByLabel('Mark invoice INV-PER-002 paid'), personaCase.canPostInvoice);
}

async function expectAccountingControls(page: Page, personaCase: PersonaCase): Promise<void> {
  await page.goto(`${BASE}/app/accounting/journals`, { waitUntil: 'domcontentloaded' });

  await expect(page.getByRole('heading', { name: 'Journal Entries' })).toBeVisible();
  if (personaCase.canPostJournal) {
    await expect(page.getByLabel('New Journal Entry')).toBeVisible();
  } else {
    await expect(page.getByLabel('New Journal Entry')).toHaveCount(0);
  }
  if (personaCase.canRunClose) {
    await expect(page.getByRole('button', { name: /Close package/i })).toBeVisible();
  } else {
    await expect(page.getByRole('button', { name: /Close package/i })).toHaveCount(0);
  }
}

async function expectReportsRead(page: Page): Promise<void> {
  await page.goto(`${BASE}/app/reports`, { waitUntil: 'domcontentloaded' });

  await expect(page.getByRole('heading', { name: 'Reports' })).toBeVisible();
  await expect(page.getByRole('tab', { name: 'AR Aging' })).toBeVisible();
  await expect(page.getByRole('tab', { name: 'Balance Sheet' })).toBeVisible();
  await expect(page.getByRole('tab', { name: 'Trial Balance' })).toBeVisible();
}

async function expectViewerDirectMutationsForbidden(page: Page): Promise<void> {
  const statuses = await page.evaluate(async () => {
    const requests = [
      { url: '/api/v1/bills', method: 'POST', body: { bill_number: 'BILL-DENIED' } },
      { url: '/api/v1/procurement/documents', method: 'POST', body: { document_type: 'purchase_order' } },
      { url: '/api/v1/invoices/inv-approved/send', method: 'POST', body: {} },
      { url: '/api/v1/accounting/journal-entries', method: 'POST', body: { lines: [] } },
      { url: '/api/v1/approval-policy/default', method: 'PUT', body: {} },
    ];
    return Promise.all(requests.map(async request => {
      const response = await fetch(request.url, {
        method: request.method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request.body),
      });
      return response.status;
    }));
  });
  expect(statuses).toEqual([403, 403, 403, 403, 403]);
}

async function expectControl(locator: Locator, enabled: boolean): Promise<void> {
  if (enabled) {
    await expect(locator).toBeEnabled();
  } else {
    await expect(locator).toBeDisabled();
  }
}

function roleLabel(role: MockRole): string {
  return {
    owner: 'Owner',
    admin: 'Admin',
    manager: 'Manager',
    approver: 'Finance Approver',
    auditor: 'Auditor',
    viewer: 'Viewer',
  }[role];
}

test.describe('Enterprise finance persona matrix (#321)', () => {
  for (const personaCase of personaCases) {
    test(`${personaCase.persona} persona maps to enforced ${personaCase.role} controls`, async ({ page }) => {
      await installPersonaMocks(page, personaCase.role);
      await authenticate(page, personaCase.role);

      await expectSettingsMatrix(page, personaCase);
      await expectInboxPolicy(page, personaCase);
      await expectBillsControls(page, personaCase);
      await expectInvoiceControls(page, personaCase);
      await expectAccountingControls(page, personaCase);
      await expectReportsRead(page);

      if (personaCase.readOnly) {
        await expectViewerDirectMutationsForbidden(page);
      }
    });
  }
});
