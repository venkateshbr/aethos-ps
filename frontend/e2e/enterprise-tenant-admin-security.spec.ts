/**
 * Tenant Admin security administration proof.
 *
 * This mocked browser spec verifies the Settings UI wiring for Dynamics-style
 * roles, duties, tenant user provisioning, and first-login password flags.
 */

import { expect, Page, test } from '@playwright/test';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'http://localhost:4201';

const securityPrivileges = [
  {
    code: 'tenant.users.manage',
    label: 'Manage tenant users',
    category: 'Security',
    description: 'Create, update, deactivate, and assign tenant users.',
  },
  {
    code: 'security.roles.manage',
    label: 'Manage security roles',
    category: 'Security',
    description: 'Create tenant roles and assign permission sets.',
  },
  {
    code: 'inbox.approve_manager',
    label: 'Approve manager work',
    category: 'Controls',
    description: 'Approve manager-threshold work.',
  },
];

const securityDuties = [
  {
    code: 'security_administration',
    label: 'Security administration',
    description: 'Manage roles, permission sets, and user assignments.',
    privileges: securityPrivileges.slice(0, 2),
  },
  {
    code: 'manager_approval',
    label: 'Manager-threshold approval',
    description: 'Approve manager-threshold Inbox work.',
    privileges: [securityPrivileges[2]],
  },
];

const seededRoles = [
  {
    id: 'role-tenant-admin',
    code: 'tenant_admin',
    label: 'Tenant Admin',
    description: 'Tenant security and configuration administrator.',
    legacy_role: 'admin',
    is_system: true,
    is_assignable: true,
    rank: 90,
    duties: securityDuties,
    privilege_codes: securityPrivileges.map(privilege => privilege.code),
  },
  {
    id: 'role-finance-approver',
    code: 'finance_approver',
    label: 'Finance Approver',
    description: 'Dedicated approval-only reviewer for manager-threshold work.',
    legacy_role: 'approver',
    is_system: true,
    is_assignable: true,
    rank: 60,
    duties: [securityDuties[1]],
    privilege_codes: ['inbox.approve_manager'],
  },
  {
    id: 'role-auditor',
    code: 'auditor',
    label: 'Auditor',
    description: 'Read-only reviewer for reports and audit evidence.',
    legacy_role: 'auditor',
    is_system: true,
    is_assignable: true,
    rank: 20,
    duties: [],
    privilege_codes: [],
  },
];

async function authenticateTenantAdmin(page: Page): Promise<void> {
  await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    window.localStorage.setItem('aethos_token', 'mock-token-admin');
    window.localStorage.setItem('aethos_tenant_id', 'tenant-admin-security');
    window.localStorage.setItem('aethos_role', 'admin');
  });
}

async function installSecurityMocks(page: Page): Promise<{
  createdRolePayloads: unknown[];
  createdUserPayloads: unknown[];
}> {
  const createdRolePayloads: unknown[] = [];
  const createdUserPayloads: unknown[] = [];
  const roles = [...seededRoles];
  const users: unknown[] = [
    {
      id: 'tenant-user-admin',
      tenant_id: 'tenant-admin-security',
      user_id: 'admin-user',
      email: 'tenant.admin@example.test',
      display_name: 'Tenant Admin',
      role: 'admin',
      role_codes: ['tenant_admin'],
      role_labels: ['Tenant Admin'],
      status: 'active',
      must_change_password: false,
      invited_at: null,
      joined_at: '2026-06-30T00:00:00Z',
      created_at: '2026-06-30T00:00:00Z',
      updated_at: '2026-06-30T00:00:00Z',
      deactivated_at: null,
    },
  ];

  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path.endsWith('/security/roles') && request.method() === 'GET') {
      await route.fulfill({ json: { items: roles, total: roles.length } });
      return;
    }
    if (path.endsWith('/security/roles') && request.method() === 'POST') {
      const payload = request.postDataJSON();
      createdRolePayloads.push(payload);
      const role = {
        id: 'role-demo-billing-reviewer',
        code: 'demo_billing_reviewer',
        label: payload.label,
        description: payload.description ?? '',
        legacy_role: payload.legacy_role,
        is_system: false,
        is_assignable: true,
        rank: 60,
        duties: [securityDuties[1]],
        privilege_codes: ['inbox.approve_manager'],
      };
      roles.push(role);
      await route.fulfill({ status: 201, json: role });
      return;
    }
    if (path.endsWith('/tenant-users') && request.method() === 'GET') {
      await route.fulfill({ json: { items: users, total: users.length } });
      return;
    }
    if (path.endsWith('/tenant-users') && request.method() === 'POST') {
      const payload = request.postDataJSON();
      createdUserPayloads.push(payload);
      const user = {
        id: 'tenant-user-approver',
        tenant_id: 'tenant-admin-security',
        user_id: 'approver-user',
        email: payload.email,
        display_name: payload.display_name,
        role: 'approver',
        role_codes: payload.role_codes,
        role_labels: ['Finance Approver'],
        status: 'active',
        must_change_password: true,
        invited_at: '2026-06-30T00:00:00Z',
        joined_at: '2026-06-30T00:00:00Z',
        created_at: '2026-06-30T00:00:00Z',
        updated_at: '2026-06-30T00:00:00Z',
        deactivated_at: null,
        set_password_url: 'https://set-password.example.test/recovery',
        temp_password: null,
      };
      users.push(user);
      await route.fulfill({ status: 201, json: user });
      return;
    }
    if (path.endsWith('/tenants/finance-personas')) {
      await route.fulfill({ json: { items: [] } });
      return;
    }
    if (path.endsWith('/approval-policy/effective')) {
      await route.fulfill({
        json: {
          tenant_id: 'tenant-admin-security',
          policy_source: 'tenant_default',
          money_out_default_role: 'owner',
          money_out_owner_threshold: '25000',
          money_out_owner_role: 'owner',
          accounting_role: 'admin',
          money_in_role: 'manager',
          draft_role: 'manager',
          external_send_role: 'admin',
          high_risk_role: 'owner',
          created_at: '2026-06-30T00:00:00Z',
          updated_at: '2026-06-30T00:00:00Z',
        },
      });
      return;
    }
    if (path.endsWith('/tenants/health')) {
      await route.fulfill({
        json: {
          status: 'ok',
          generated_at: '2026-06-30T00:00:00Z',
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
            window_start: '2026-06-30T00:00:00Z',
          },
          alerts: { route: { route_type: 'runbook_queue', channel: 'runbook', configured: false }, items: [] },
        },
      });
      return;
    }
    if (request.method() === 'GET') {
      await route.fulfill({ json: { items: [], total: 0 } });
      return;
    }

    await route.fulfill({ status: 403, json: { detail: 'Mocked denial' } });
  });

  return { createdRolePayloads, createdUserPayloads };
}

test.describe('Tenant Admin security administration', () => {
  test('creates tenant roles and users with first-login password controls', async ({ page }) => {
    const mocks = await installSecurityMocks(page);
    await authenticateTenantAdmin(page);

    await page.goto(`${BASE}/app/settings`, { waitUntil: 'domcontentloaded' });

    await expect(page.getByRole('heading', { name: 'Security Roles' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Tenant Users' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Tenant Admin' })).toBeVisible();

    await page.getByLabel('Role name').fill('Demo Billing Reviewer');
    await page.getByLabel('Legacy projection').selectOption('approver');
    await page.getByLabel('Description').fill('Reviews demo billing approvals.');
    await page.getByLabel('Manager-threshold approval').check();
    await page.getByRole('button', { name: /^Create Role$/ }).click();

    await expect(page.getByText('Role created.')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Demo Billing Reviewer' })).toBeVisible();
    expect(mocks.createdRolePayloads).toEqual([
      {
        label: 'Demo Billing Reviewer',
        description: 'Reviews demo billing approvals.',
        legacy_role: 'approver',
        duty_codes: ['manager_approval'],
      },
    ]);

    const inviteForm = page.locator('form').filter({ hasText: 'Invite user' });
    await inviteForm.getByLabel('Email').fill('finance.approver@example.test');
    await inviteForm.getByLabel('Display name').fill('Finance Approver');
    await inviteForm.getByLabel('Role').selectOption('finance_approver');
    await inviteForm.getByLabel('Temporary password').fill('InitialPass!2026');
    await inviteForm.getByRole('button', { name: /^Create User$/ }).click();

    await expect(page.getByText('User invited: finance.approver@example.test')).toBeVisible();
    await expect(page.getByText('Initial password change required')).toBeVisible();
    expect(mocks.createdUserPayloads).toEqual([
      {
        email: 'finance.approver@example.test',
        role_codes: ['finance_approver'],
        display_name: 'Finance Approver',
        password: 'InitialPass!2026',
      },
    ]);
  });
});
