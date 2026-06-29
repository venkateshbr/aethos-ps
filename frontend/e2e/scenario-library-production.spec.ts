/**
 * Production runner for tests/Aethos-PS-Test-Scenario-Library.md.
 *
 * This runner creates the ten scenario-library tenants through the deployed
 * Aethos signup API, creates one signature client/engagement/project/employee
 * per tenant through product APIs, verifies the live UI, sends one Atlas prompt
 * per tenant, and validates independent Timesheet Portal login/time logging.
 *
 * It intentionally avoids direct database writes. The only non-browser setup
 * calls are the same public/authenticated HTTP routes used by the frontend.
 */

import { expect, test, type APIRequestContext, type Page } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

const WEB = process.env.AETHOS_PS_WEB_URL ?? 'https://aethos.ishirock.tech';
const TIMESHEET = process.env.AETHOS_TS_WEB_URL ?? 'https://timesheet.aethos.ishirock.tech';
const RUN_ID = new Date().toISOString().replace(/[:.]/g, '-');
const REPO_ROOT = path.resolve(__dirname, '../..');
const QA_DIR = path.join(REPO_ROOT, 'docs', 'qa', `scenario-library-production-${RUN_ID}`);
const SHOT_DIR = path.join(QA_DIR, 'screenshots');
const REPORT_PATH = path.join(QA_DIR, 'report.md');
const JSON_PATH = path.join(QA_DIR, 'results.json');
const CREDENTIALS_PATH = path.join(REPO_ROOT, 'demo_credentials.json');

type Status = 'PASS' | 'FAIL' | 'WARN' | 'SKIP';
type TenantSpec = {
  id: string;
  name: string;
  country: 'US' | 'GB' | 'SG' | 'IN' | 'AU';
  currency: string;
  client: string;
  engagement: string;
  project: string;
  billing: 'time_and_materials' | 'fixed_fee' | 'retainer' | 'retainer_draw' | 'milestone' | 'capped_tm' | 'mixed';
  serviceLine: 'accounting' | 'tax' | 'cosec' | 'payroll' | 'advisory' | 'other';
  totalValue: string;
  prompt: string;
};
type TenantResult = {
  spec: TenantSpec;
  owner: { email: string; password: string; tenantId?: string };
  employee: { email: string; password: string; employeeId?: string };
  erpUser: { email: string; password: string; role: 'manager'; tenantUserId?: string };
  records: { clientId?: string; engagementId?: string; projectId?: string };
  checks: Evidence[];
};
type Evidence = {
  id: string;
  tenant: string;
  action: string;
  status: Status;
  notes?: string[];
  screenshot?: string;
  response?: string;
};

const tenantSpecs: TenantSpec[] = [
  {
    id: 'T1',
    name: 'Cobalt Consulting Co.',
    country: 'US',
    currency: 'USD',
    client: 'Riverbend Foods',
    engagement: 'Riverbend Discovery Advisory',
    project: 'Riverbend Discovery Project',
    billing: 'time_and_materials',
    serviceLine: 'advisory',
    totalValue: '25000.00',
    prompt: 'Show me the Riverbend Foods engagement structure. List active projects, billing model, linked source data, and anything missing before billing.',
  },
  {
    id: 'T2',
    name: 'Pixel & Pulp Studio',
    country: 'GB',
    currency: 'GBP',
    client: 'Aurora Cosmetics',
    engagement: 'Aurora Web Build SOW',
    project: 'Aurora Milestone 1 Build',
    billing: 'milestone',
    serviceLine: 'advisory',
    totalValue: '45000.00',
    prompt: 'Show me the Aurora Cosmetics milestone engagement. Include projects, milestone billing model, WIP readiness, and missing setup before invoicing.',
  },
  {
    id: 'T3',
    name: 'Harborstone Accountants',
    country: 'US',
    currency: 'USD',
    client: 'Delmont Holdings',
    engagement: 'Delmont Annual Accounts FY2026',
    project: 'Delmont Accounts Drafting',
    billing: 'fixed_fee',
    serviceLine: 'accounting',
    totalValue: '18500.00',
    prompt: 'Show me the Delmont Holdings annual accounts engagement. Include service line, billing terms, projects, and year-end reporting readiness.',
  },
  {
    id: 'T4',
    name: 'Vantage Tax Partners',
    country: 'SG',
    currency: 'SGD',
    client: 'Pacific Rim Holdings',
    engagement: 'Pacific Rim Cross-Border Tax',
    project: 'Pacific Rim FX Advisory',
    billing: 'capped_tm',
    serviceLine: 'tax',
    totalValue: '38000.00',
    prompt: 'Review Pacific Rim cross-border tax readiness. Include FX provenance needs, capped T&M terms, project setup, and missing evidence before billing.',
  },
  {
    id: 'T5',
    name: 'Indus Engineering Advisory',
    country: 'IN',
    currency: 'INR',
    client: 'Deccan Metro Authority',
    engagement: 'Deccan Metro PMO Program',
    project: 'Deccan Metro Phase 1 PMO',
    billing: 'milestone',
    serviceLine: 'advisory',
    totalValue: '7500000.00',
    prompt: 'Show me Deccan Metro PMO delivery and billing readiness. Include milestone program setup, procurement risks, WIP, and AP controls to verify.',
  },
  {
    id: 'T6',
    name: 'Southern Cross Legal',
    country: 'AU',
    currency: 'AUD',
    client: 'Brindabella Ventures',
    engagement: 'Brindabella Retainer Draw',
    project: 'Brindabella Matter Support',
    billing: 'retainer_draw',
    serviceLine: 'advisory',
    totalValue: '60000.00',
    prompt: 'Show me Brindabella retainer-draw status. Include project setup, retainer floor risk, invoice readiness, and any collection hold considerations.',
  },
  {
    id: 'T7',
    name: 'Atlas Capital Advisors',
    country: 'US',
    currency: 'USD',
    client: 'Redwood Industrials',
    engagement: 'Redwood Sell-Side M&A',
    project: 'Redwood Deal Execution',
    billing: 'milestone',
    serviceLine: 'advisory',
    totalValue: '465000.00',
    prompt: 'Review Redwood sell-side M&A billing readiness. Include success-fee milestone logic, approval boundary, FX considerations, and evidence needed before invoicing.',
  },
  {
    id: 'T8',
    name: 'Helix Talent Group',
    country: 'GB',
    currency: 'GBP',
    client: 'Halcyon Retail',
    engagement: 'Halcyon RPO Retainer',
    project: 'Halcyon Monthly Talent Ops',
    billing: 'retainer',
    serviceLine: 'payroll',
    totalValue: '72000.00',
    prompt: 'Show me Halcyon RPO retainer readiness. Include per-period billing, project staffing, utilization, and month-end reporting implications.',
  },
  {
    id: 'T9',
    name: 'Brightline Wealth Office',
    country: 'GB',
    currency: 'GBP',
    client: 'Ashford Family Office',
    engagement: 'Ashford Family Office Advisory',
    project: 'Ashford COSEC and Tax Coordination',
    billing: 'mixed',
    serviceLine: 'cosec',
    totalValue: '125000.00',
    prompt: 'Show me the Ashford Family Office structure. Include engagements, service lines, billing models, currencies, open projects, privacy risks, and missing setup before billing.',
  },
  {
    id: 'T10',
    name: 'Quantum Systems Integration',
    country: 'US',
    currency: 'USD',
    client: 'Continental Insurance Group',
    engagement: 'Continental Enterprise Transformation',
    project: 'Continental Workstream A',
    billing: 'mixed',
    serviceLine: 'advisory',
    totalValue: '950000.00',
    prompt: 'Run today\'s finance ops check for Continental and Quantum. Separate read-only findings from actions that need Inbox approval. Include AR, AP, WIP, close, controls, and operational health.',
  },
];

const allResults: TenantResult[] = [];
const globalEvidence: Evidence[] = [];

function envValue(name: string): string {
  if (process.env[name]) return process.env[name]!;
  for (const file of [path.join(REPO_ROOT, '.env'), path.join(REPO_ROOT, 'backend', '.env')]) {
    if (!fs.existsSync(file)) continue;
    const line = fs
      .readFileSync(file, 'utf-8')
      .split(/\r?\n/)
      .find((row) => row.trim().startsWith(`${name}=`));
    if (line) return line.slice(line.indexOf('=') + 1).trim().replace(/^['"]|['"]$/g, '');
  }
  return '';
}

function rel(file: string): string {
  return path.relative(REPO_ROOT, file).replace(/\\/g, '/');
}

function redact(value: string): string {
  return value
    .replace(/https:\/\/openrouter\.ai\/workspaces\/[^\s<)]+/gi, '[redacted-provider-url]')
    .replace(/sk-or-v1-[A-Za-z0-9_-]+/g, '[redacted-api-key]')
    .replace(/Bearer\s+[A-Za-z0-9._-]+/gi, 'Bearer [redacted]')
    .replace(/access_token["']?\s*:\s*["'][^"']+/gi, 'access_token":"[redacted]');
}

async function shot(page: Page, id: string): Promise<string> {
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  const file = path.join(SHOT_DIR, `${id.replace(/[^a-zA-Z0-9_.-]/g, '-')}.png`);
  await page.screenshot({ path: file, fullPage: false }).catch(() => undefined);
  return rel(file);
}

function evidence(result: TenantResult | null, item: Evidence): void {
  const sanitized: Evidence = {
    ...item,
    notes: item.notes?.map(redact),
    response: item.response ? redact(item.response) : undefined,
  };
  if (result) result.checks.push(sanitized);
  globalEvidence.push(sanitized);
  console.log(`[${sanitized.status}] ${sanitized.tenant} ${sanitized.id} - ${sanitized.action}`);
  if (sanitized.notes?.length) console.log(`      ${sanitized.notes.join(' | ')}`);
}

async function apiJson<T>(
  request: APIRequestContext,
  method: 'get' | 'post',
  url: string,
  options: Parameters<APIRequestContext['post']>[1] = {},
): Promise<T> {
  const response = method === 'get'
    ? await request.get(url, options)
    : await request.post(url, options);
  if (!response.ok()) {
    const body = await response.text().catch(() => '');
    throw new Error(`${method.toUpperCase()} ${url} failed: HTTP ${response.status()} ${body.slice(0, 500)}`);
  }
  return await response.json() as T;
}

async function signInWithSupabase(
  request: APIRequestContext,
  email: string,
  password: string,
): Promise<string> {
  const supabaseUrl = envValue('SUPABASE_URL');
  const anonKey = envValue('SUPABASE_ANON_KEY');
  if (!supabaseUrl || !anonKey) throw new Error('SUPABASE_URL and SUPABASE_ANON_KEY are required for production login validation.');
  const body = await apiJson<{ access_token?: string }>(
    request,
    'post',
    `${supabaseUrl}/auth/v1/token?grant_type=password`,
    {
      headers: { apikey: anonKey, 'Content-Type': 'application/json' },
      data: { email, password },
      timeout: 60_000,
    },
  );
  if (!body.access_token) throw new Error(`Supabase sign-in returned no access_token for ${email}`);
  return body.access_token;
}

function authHeaders(token: string, tenantId: string): Record<string, string> {
  return {
    Authorization: `Bearer ${token}`,
    'X-Tenant-ID': tenantId,
    'Content-Type': 'application/json',
  };
}

function billingTerms(spec: TenantSpec): Record<string, unknown> {
  switch (spec.billing) {
    case 'fixed_fee':
      return { fixed_fee_amount: spec.totalValue };
    case 'milestone':
      return { milestone_total: spec.totalValue };
    case 'retainer':
      return { retainer_monthly_amount: '6000.00' };
    case 'retainer_draw':
      return { retainer_monthly_amount: '7500.00', retainer_floor: '10000.00', retainer_rollover: true };
    case 'capped_tm':
      return { cap_amount: spec.totalValue };
    case 'mixed':
      return { fixed_fee_amount: '25000.00', retainer_monthly_amount: '8000.00', cap_amount: spec.totalValue };
    case 'time_and_materials':
    default:
      return {};
  }
}

async function createTenantData(request: APIRequestContext, spec: TenantSpec): Promise<TenantResult> {
  const stamp = RUN_ID.replace(/[^0-9TZ-]/g, '').slice(0, 19).toLowerCase();
  const suffix = `${spec.id.toLowerCase()}-${stamp}`;
  const ownerPassword = `Aethos-${spec.id}-Owner-2026!`;
  const employeePassword = `Aethos-${spec.id}-Employee-2026!`;
  const erpUserPassword = `Aethos-${spec.id}-Manager-2026!`;
  const ownerEmail = `prod-${suffix}-owner@aethos-qa.dev`;
  const employeeEmail = `prod-${suffix}-employee@aethos-qa.dev`;
  const erpUserEmail = `prod-${suffix}-manager@aethos-qa.dev`;
  const result: TenantResult = {
    spec,
    owner: { email: ownerEmail, password: ownerPassword },
    employee: { email: employeeEmail, password: employeePassword },
    erpUser: { email: erpUserEmail, password: erpUserPassword, role: 'manager' },
    records: {},
    checks: [],
  };

  try {
    const signup = await apiJson<{ tenant_id: string }>(request, 'post', `${WEB}/api/v1/auth/signup`, {
      data: {
        email: ownerEmail,
        password: ownerPassword,
        tenant_name: `${spec.name} ${stamp}`,
        country: spec.country,
        plan_tier: 'growth',
        billing_interval: 'monthly',
      },
      timeout: 90_000,
    });
    result.owner.tenantId = signup.tenant_id;
    evidence(result, {
      id: `${spec.id}-signup`,
      tenant: spec.name,
      action: 'Created tenant through production signup API',
      status: 'PASS',
      notes: [`tenant_id=${signup.tenant_id}`, `owner=${ownerEmail}`],
    });

    const ownerToken = await signInWithSupabase(request, ownerEmail, ownerPassword);
    const headers = authHeaders(ownerToken, signup.tenant_id);
    const erpUser = await apiJson<{ id: string; email: string; role: string }>(request, 'post', `${WEB}/api/v1/tenant-users`, {
      headers,
      data: {
        email: erpUserEmail,
        password: erpUserPassword,
        role: 'manager',
        display_name: `${spec.id} Finance Ops Manager`,
      },
      timeout: 60_000,
    });
    result.erpUser.tenantUserId = erpUser.id;

    const client = await apiJson<{ id: string }>(request, 'post', `${WEB}/api/v1/clients`, {
      headers,
      data: {
        name: spec.client,
        kind: 'customer',
        email: `${spec.client.toLowerCase().replace(/[^a-z0-9]+/g, '.')}@example.test`,
        payment_terms_days: 30,
      },
      timeout: 60_000,
    });
    result.records.clientId = client.id;

    const engagement = await apiJson<{ id: string }>(request, 'post', `${WEB}/api/v1/engagements`, {
      headers,
      data: {
        client_id: client.id,
        name: spec.engagement,
        billing_arrangement: spec.billing,
        currency: spec.currency,
        total_value: spec.totalValue,
        description: `Production scenario-library ${spec.id} engagement.`,
        start_date: '2026-06-01',
        end_date: '2026-12-31',
        service_line: spec.serviceLine,
        billing_terms: billingTerms(spec),
      },
      timeout: 60_000,
    });
    result.records.engagementId = engagement.id;

    const project = await apiJson<{ id: string }>(request, 'post', `${WEB}/api/v1/projects`, {
      headers,
      data: {
        engagement_id: engagement.id,
        name: spec.project,
        description: `Production scenario-library ${spec.id} project.`,
        status: 'active',
        currency: spec.currency,
        budget: spec.totalValue,
        budget_hours: '120.00',
        start_date: '2026-06-01',
        end_date: '2026-12-31',
      },
      timeout: 60_000,
    });
    result.records.projectId = project.id;

    const employee = await apiJson<{ id: string }>(request, 'post', `${WEB}/api/v1/employees`, {
      headers,
      data: {
        first_name: `${spec.id} Employee`,
        last_name: 'Tester',
        email: employeeEmail,
        title: 'Consultant',
        department: spec.serviceLine,
        employment_type: 'full_time',
        default_bill_rate: '175.00',
        default_bill_rate_currency: spec.currency,
        cost_rate: '85.00',
        available_hours_per_week: '40.00',
        target_billable_utilization_pct: '75.00',
        practice_area: spec.serviceLine === 'other' ? 'advisory' : spec.serviceLine,
        seniority: 'senior',
      },
      timeout: 60_000,
    });
    result.employee.employeeId = employee.id;

    await apiJson<{ email: string; role: string }>(request, 'post', `${WEB}/api/v1/employees/${employee.id}/invite`, {
      headers,
      data: { password: employeePassword },
      timeout: 60_000,
    });

    await apiJson<{ id: string }>(request, 'post', `${WEB}/api/v1/projects/${project.id}/assignments`, {
      headers,
      data: {
        employee_id: employee.id,
        role: 'Consultant',
        override_rate: '175.00',
        start_date: '2026-06-01',
      },
      timeout: 60_000,
    });

    evidence(result, {
      id: `${spec.id}-master-data`,
      tenant: spec.name,
      action: 'Created signature client, engagement, project, employee login, and project assignment',
      status: 'PASS',
      notes: [
        `client=${spec.client}`,
        `project=${spec.project}`,
        `erp_user=${erpUserEmail}`,
        `employee=${employeeEmail}`,
      ],
    });
  } catch (err) {
    evidence(result, {
      id: `${spec.id}-setup`,
      tenant: spec.name,
      action: 'Create tenant scenario data',
      status: 'FAIL',
      notes: [String(err).slice(0, 900)],
    });
  }

  return result;
}

async function ownerLogin(page: Page, result: TenantResult): Promise<void> {
  await page.goto(`${WEB}/login`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
  await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible({ timeout: 30_000 });
  await page.locator('#email, input[type="email"]').first().fill(result.owner.email);
  await page.locator('#password, input[type="password"]').first().fill(result.owner.password);
  await page.getByRole('button', { name: /^sign in$/i }).click();
  await page.waitForURL(/\/app\/copilot(\?.*)?$/, { timeout: 90_000 });
  await expect(page.getByRole('button', { name: /new chat/i })).toBeVisible({ timeout: 30_000 });
}

async function checkRoute(page: Page, result: TenantResult, route: string, label: string): Promise<void> {
  try {
    await page.goto(`${WEB}${route}`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await page.waitForLoadState('networkidle', { timeout: 8_000 }).catch(() => undefined);
    const text = (await page.locator('body').innerText({ timeout: 8_000 }).catch(() => '')).replace(/\s+/g, ' ');
    const status: Status = /failed to load|error loading|something went wrong/i.test(text) ? 'WARN' : 'PASS';
    const screenshot = await shot(page, `${result.spec.id}-${label}`);
    evidence(result, {
      id: `${result.spec.id}-${label}`,
      tenant: result.spec.name,
      action: `Live route ${route}`,
      status,
      screenshot,
      notes: [`Body excerpt: ${text.slice(0, 180)}`],
    });
  } catch (err) {
    evidence(result, {
      id: `${result.spec.id}-${label}`,
      tenant: result.spec.name,
      action: `Live route ${route}`,
      status: 'FAIL',
      notes: [String(err).slice(0, 500)],
    });
  }
}

async function erpUserLoginAndRead(page: Page, result: TenantResult): Promise<void> {
  try {
    await page.goto(`${WEB}/login`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible({ timeout: 30_000 });
    await page.locator('#email, input[type="email"]').first().fill(result.erpUser.email);
    await page.locator('#password, input[type="password"]').first().fill(result.erpUser.password);
    await page.getByRole('button', { name: /^sign in$/i }).click();
    await page.waitForURL(/\/app\/copilot(\?.*)?$/, { timeout: 90_000 });
    await expect(page.getByRole('button', { name: /new chat/i })).toBeVisible({ timeout: 30_000 });
    await page.goto(`${WEB}/app/reports`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await page.waitForLoadState('networkidle', { timeout: 8_000 }).catch(() => undefined);
    const body = (await page.locator('body').innerText({ timeout: 8_000 }).catch(() => '')).replace(/\s+/g, ' ');
    const status: Status = /failed to load|error loading|something went wrong/i.test(body) ? 'WARN' : 'PASS';
    evidence(result, {
      id: `${result.spec.id}-erp-manager-login`,
      tenant: result.spec.name,
      action: 'ERP manager login to live Aethos app',
      status,
      screenshot: await shot(page, `${result.spec.id}-erp-manager-login`),
      notes: [
        `Manager ${result.erpUser.email} logged in independently.`,
        `Reports body excerpt: ${body.slice(0, 180)}`,
      ],
    });
  } catch (err) {
    evidence(result, {
      id: `${result.spec.id}-erp-manager-login`,
      tenant: result.spec.name,
      action: 'ERP manager login to live Aethos app',
      status: 'FAIL',
      notes: [String(err).slice(0, 900)],
    });
  }
}

async function askAtlas(page: Page, result: TenantResult): Promise<void> {
  try {
    await page.goto(`${WEB}/app/copilot`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    const newChat = page.getByRole('button', { name: /new chat|start new chat/i }).first();
    if (await newChat.isVisible({ timeout: 8_000 }).catch(() => false)) await newChat.click();
    const before = await page.locator('[aria-label^="Atlas:"]').count();
    const input = page.getByLabel('Message input');
    await expect(input).toBeEnabled({ timeout: 45_000 });
    await input.fill(result.spec.prompt);
    await page.getByRole('button', { name: /send message/i }).click();
    await page.locator('[aria-label^="Atlas:"]').nth(before).waitFor({ state: 'visible', timeout: 180_000 }).catch(() => undefined);
    await expect(input).toBeEnabled({ timeout: 180_000 }).catch(() => undefined);
    await page.waitForTimeout(1000);
    const response = await page.locator('[aria-label^="Atlas:"]').last().innerText().catch(() => '');
    const screenshot = await shot(page, `${result.spec.id}-atlas-response`);
    const required = [new RegExp(result.spec.client.split(' ')[0], 'i'), /engagement|project|billing|finance|WIP|readiness/i];
    const missing = required.filter((pattern) => !pattern.test(response)).map((pattern) => pattern.source);
    const invalid = /context_ref|traceback|stack trace|aethos\.[a-z0-9_.]+|tool completed|running tool/i.test(response);
    evidence(result, {
      id: `${result.spec.id}-atlas`,
      tenant: result.spec.name,
      action: 'Atlas scenario-library prompt',
      status: response && !missing.length && !invalid ? 'PASS' : 'FAIL',
      screenshot,
      response,
      notes: [
        `Prompt: ${result.spec.prompt}`,
        response ? `Response excerpt: ${response.replace(/\s+/g, ' ').slice(0, 280)}` : 'No Atlas response captured.',
        missing.length ? `Missing required response signals: ${missing.join(', ')}` : 'Required business signals present.',
        invalid ? 'Response exposed internal/tool/error terminology.' : 'No internal tool terminology detected.',
      ],
    });
  } catch (err) {
    evidence(result, {
      id: `${result.spec.id}-atlas`,
      tenant: result.spec.name,
      action: 'Atlas scenario-library prompt',
      status: 'FAIL',
      notes: [String(err).slice(0, 700)],
    });
  }
}

async function timesheetLoginAndLog(page: Page, result: TenantResult): Promise<void> {
  try {
    await page.goto(`${TIMESHEET}/login`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible({ timeout: 30_000 });
    await page.locator('input[type="email"]').fill(result.employee.email);
    await page.locator('input[type="password"]').fill(result.employee.password);
    await page.getByRole('button', { name: /^sign in$/i }).click();
    await page.waitForURL(/\/timesheet$/, { timeout: 60_000 });
    await expect(page.getByRole('heading', { name: /my week/i })).toBeVisible({ timeout: 30_000 });
    await expect(page.locator('.animate-spin')).toHaveCount(0, { timeout: 60_000 });
    const bodyBefore = (await page.locator('body').innerText({ timeout: 8_000 }).catch(() => '')).replace(/\s+/g, ' ');
    if (/No projects assigned/i.test(bodyBefore)) {
      evidence(result, {
        id: `${result.spec.id}-timesheet`,
        tenant: result.spec.name,
        action: 'Timesheet employee login and time entry',
        status: 'FAIL',
        screenshot: await shot(page, `${result.spec.id}-timesheet-no-project`),
        notes: ['Employee could log in but no assigned project was visible.'],
      });
      return;
    }
    const firstInput = page.locator('input[type="number"]').first();
    await expect(firstInput).toBeVisible({ timeout: 30_000 });
    await firstInput.fill('2.5');
    await firstInput.dispatchEvent('change');
    await expect(page.getByText(/draft entr/i)).toBeVisible({ timeout: 30_000 });
    const submit = page.getByRole('button', { name: /submit week/i });
    await expect(submit).toBeEnabled({ timeout: 30_000 });
    await submit.click();
    await expect(page.locator('p.text-sm.text-text-muted', { hasText: /submitted and awaiting approval/i })).toBeVisible({ timeout: 60_000 });
    evidence(result, {
      id: `${result.spec.id}-timesheet`,
      tenant: result.spec.name,
      action: 'Timesheet employee login and time entry',
      status: 'PASS',
      screenshot: await shot(page, `${result.spec.id}-timesheet-submitted`),
      notes: [`Employee ${result.employee.email} logged in independently and submitted 2.5 hours.`],
    });
  } catch (err) {
    evidence(result, {
      id: `${result.spec.id}-timesheet`,
      tenant: result.spec.name,
      action: 'Timesheet employee login and time entry',
      status: 'FAIL',
      notes: [String(err).slice(0, 900)],
    });
  }
}

function writeCredentials(results: TenantResult[]): void {
  const existing = fs.existsSync(CREDENTIALS_PATH)
    ? JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf-8'))
    : {};
  existing.production_scenario_library_latest = {
    run_id: RUN_ID,
    base_url: WEB,
    timesheet_url: TIMESHEET,
    tenants: results.map((result) => ({
      scenario: result.spec.id,
      tenant_name: result.spec.name,
      tenant_id: result.owner.tenantId,
      owner: {
        email: result.owner.email,
        password: result.owner.password,
        role: 'owner',
      },
      timesheet_employee: {
        email: result.employee.email,
        password: result.employee.password,
        role: 'employee',
        employee_id: result.employee.employeeId,
      },
      erp_manager: {
        email: result.erpUser.email,
        password: result.erpUser.password,
        role: result.erpUser.role,
        tenant_user_id: result.erpUser.tenantUserId,
      },
      records: result.records,
    })),
  };
  existing.updated_at = new Date().toISOString();
  fs.writeFileSync(CREDENTIALS_PATH, `${JSON.stringify(existing, null, 2)}\n`);
}

function writeReport(results: TenantResult[]): void {
  fs.mkdirSync(QA_DIR, { recursive: true });
  const counts = globalEvidence.reduce<Record<Status, number>>((acc, item) => {
    acc[item.status] += 1;
    return acc;
  }, { PASS: 0, WARN: 0, FAIL: 0, SKIP: 0 });
  const rows = globalEvidence.map((item) => (
    `| ${item.tenant} | ${item.id} | ${item.action.replace(/\|/g, '/')} | ${item.status} | ${item.screenshot ? `[screenshot](${path.relative(QA_DIR, path.join(REPO_ROOT, item.screenshot)).replace(/\\/g, '/')})` : ''} | ${(item.notes ?? []).join('<br>').replace(/\|/g, '/')} |`
  )).join('\n');
  const prompts = globalEvidence
    .filter((item) => item.response)
    .map((item) => [
      `## ${item.id} - ${item.tenant}`,
      '',
      '```text',
      (item.response ?? '').slice(0, 3000),
      '```',
    ].join('\n'))
    .join('\n\n');
  const blockedRoleSurface = [
    'Tenant-user invite exists and is used for one ERP manager per tenant.',
    'Employee invite exists and was used for independent timesheet portal validation.',
    'Auditor-specific persona remains mapped to the read-only viewer role until a distinct auditor role is added.',
  ];
  const report = [
    '# Aethos PS Test Scenario Library Production Run',
    '',
    `Run ID: \`${RUN_ID}\``,
    `Base URL: \`${WEB}\``,
    `Timesheet URL: \`${TIMESHEET}\``,
    `Generated: \`${new Date().toISOString()}\``,
    '',
    `Summary: PASS ${counts.PASS}, WARN ${counts.WARN}, FAIL ${counts.FAIL}, SKIP ${counts.SKIP}`,
    '',
    '## Scope',
    '',
    '- Created all 10 scenario-library tenants through the deployed signup API.',
    '- Created one signature client, engagement, active project, invited timesheet employee, and project assignment per tenant through authenticated product APIs.',
    '- Created one ERP manager user per tenant through the tenant-user administration API.',
    '- Validated live owner login, ERP manager login, key app routes, one Atlas business prompt per tenant, and independent timesheet login/time submission per tenant.',
    '- This run does not direct-write to the database and does not use backend seed scripts.',
    '',
    '## Known Blocked Coverage',
    '',
    blockedRoleSurface.map((line) => `- ${line}`).join('\n'),
    '',
    '## Evidence Table',
    '',
    '| Tenant | ID | Action | Status | Screenshot | Notes |',
    '| --- | --- | --- | --- | --- | --- |',
    rows,
    '',
    '## Atlas Response Excerpts',
    '',
    prompts || '_No Atlas responses captured._',
    '',
  ].join('\n');
  fs.writeFileSync(REPORT_PATH, report);
  fs.writeFileSync(JSON_PATH, JSON.stringify({ runId: RUN_ID, web: WEB, timesheet: TIMESHEET, results, evidence: globalEvidence }, null, 2));
  console.log(`Report: ${REPORT_PATH}`);
  console.log(`Results JSON: ${JSON_PATH}`);
}

test.describe('Production scenario-library ten-tenant validation', () => {
  test.describe.configure({ mode: 'serial' });

  test.afterAll(async () => {
    writeCredentials(allResults);
    writeReport(allResults);
  });

  test('creates all tenants and validates Atlas, ERP users, and timesheet on production', async ({ request, page }) => {
    test.setTimeout(45 * 60_000);

    for (const spec of tenantSpecs) {
      const result = await createTenantData(request, spec);
      allResults.push(result);
      if (
        !result.owner.tenantId
        || !result.records.projectId
        || !result.employee.employeeId
        || !result.erpUser.tenantUserId
      ) {
        evidence(result, {
          id: `${spec.id}-scenario-skipped`,
          tenant: spec.name,
          action: 'Skip live scenario checks due setup failure',
          status: 'SKIP',
        });
        continue;
      }

      try {
        await ownerLogin(page, result);
        evidence(result, {
          id: `${spec.id}-owner-login`,
          tenant: spec.name,
          action: 'Owner login to live app',
          status: 'PASS',
          screenshot: await shot(page, `${spec.id}-owner-login`),
        });
      } catch (err) {
        evidence(result, {
          id: `${spec.id}-owner-login`,
          tenant: spec.name,
          action: 'Owner login to live app',
          status: 'FAIL',
          notes: [String(err).slice(0, 700)],
        });
        continue;
      }

      const routes = spec.id === 'T1'
        ? [
          ['/app/copilot', 'copilot'],
          ['/app/clients', 'clients'],
          ['/app/engagements', 'engagements'],
          ['/app/projects', 'projects'],
          ['/app/people', 'people'],
          ['/app/time', 'time'],
          ['/app/inbox', 'inbox'],
          ['/app/invoices', 'invoices'],
          ['/app/bills', 'bills'],
          ['/app/reports', 'reports'],
          ['/app/accounting/journals', 'journals'],
          ['/app/settings', 'settings'],
        ]
        : [
          ['/app/copilot', 'copilot'],
          ['/app/clients', 'clients'],
          ['/app/engagements', 'engagements'],
          ['/app/projects', 'projects'],
          ['/app/people', 'people'],
          ['/app/reports', 'reports'],
        ];
      for (const [route, label] of routes) await checkRoute(page, result, route, label);

      await askAtlas(page, result);
      await erpUserLoginAndRead(page, result);
      await timesheetLoginAndLog(page, result);
    }

    expect(allResults).toHaveLength(10);
  });
});
