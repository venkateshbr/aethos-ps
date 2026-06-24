/**
 * Live Copilot tool-use verification for #253.
 *
 * This intentionally uses the browser for the user-facing workflow:
 * Copilot chat -> tool call -> HITL Inbox approval -> Time Entries UI.
 */

import { test, expect, APIRequestContext, APIResponse, Page } from '@playwright/test';
import { Buffer } from 'node:buffer';
import { randomUUID } from 'node:crypto';
import * as fs from 'node:fs';
import * as path from 'node:path';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'http://localhost:4201';
const STORAGE_PATH = path.join(__dirname, '.auth', 'o2c-tenant.json');
const META_PATH = path.join(__dirname, '.auth', 'o2c-tenant.meta.json');
const API_REQUEST_TIMEOUT = 90_000;
const DEMO_PROJECT_NAME = 'Advisory Services [DEMO]';
const FALLBACK_PROJECT_NAME = 'Copilot Live Time Verification [E2E]';

type AuthContext = { token: string; tenantId: string; userId: string };
type LoginCredentials = { email: string; password: string };
type SupabaseAdminConfig = { url: string; serviceRoleKey: string };
type ProjectSetup = { id: string; name: string };
type EmployeeSetup = { id: string };
type HitlTaskRow = { id: string; title: string; payload?: Record<string, unknown> };
type TimeEntryRow = {
  id: string;
  tenant_id: string;
  project_id: string;
  employee_id: string;
  hours: string | number;
  date: string;
  description: string;
  billable: boolean;
  billing_status: string;
  status?: string;
};

function envValue(name: string): string {
  if (process.env[name]) return process.env[name]!;
  for (const file of [path.join(__dirname, '..', '..', '.env'), path.join(__dirname, '..', '..', 'backend', '.env')]) {
    if (!fs.existsSync(file)) continue;
    const line = fs
      .readFileSync(file, 'utf-8')
      .split(/\r?\n/)
      .find(row => row.trim().startsWith(`${name}=`));
    if (!line) continue;
    return line.slice(line.indexOf('=') + 1).trim().replace(/^['"]|['"]$/g, '');
  }
  return '';
}

function loadLoginMeta(): LoginCredentials | null {
  if (!fs.existsSync(META_PATH)) return null;
  try {
    const meta = JSON.parse(fs.readFileSync(META_PATH, 'utf-8'));
    if (meta.email && meta.password) return { email: meta.email, password: meta.password };
  } catch { /* no-op */ }
  return null;
}

function parseJwtSub(token: string): string {
  const [, payload] = token.split('.');
  if (!payload) return '';
  try {
    return String(JSON.parse(Buffer.from(payload, 'base64url').toString('utf-8')).sub ?? '');
  } catch {
    return '';
  }
}

function getAuthFromStorage(): AuthContext | null {
  if (!fs.existsSync(STORAGE_PATH)) return null;
  try {
    const state = JSON.parse(fs.readFileSync(STORAGE_PATH, 'utf-8'));
    let token = '';
    let tenantId = '';
    for (const origin of state.origins ?? []) {
      for (const ls of origin.localStorage ?? []) {
        if (ls.name?.startsWith('sb-') && ls.name?.endsWith('-auth-token')) {
          try { token = JSON.parse(ls.value)?.access_token ?? token; } catch { /* no-op */ }
        }
        if (!token && ls.name === 'aethos_token') token = ls.value;
        if (ls.name === 'aethos_tenant_id') tenantId = ls.value;
      }
    }
    const userId = parseJwtSub(token);
    if (token && tenantId && userId) return { token, tenantId, userId };
  } catch { /* no-op */ }
  return null;
}

function supabaseAdminConfig(): SupabaseAdminConfig | null {
  const url = envValue('SUPABASE_URL');
  const serviceRoleKey = envValue('SUPABASE_SERVICE_ROLE_KEY');
  if (!url || !serviceRoleKey) return null;
  return { url, serviceRoleKey };
}

function supabaseAdminHeaders(config: SupabaseAdminConfig, extra: Record<string, string> = {}) {
  return {
    apikey: config.serviceRoleKey,
    Authorization: `Bearer ${config.serviceRoleKey}`,
    'Content-Type': 'application/json',
    ...extra,
  };
}

function restUrl(config: SupabaseAdminConfig, table: string, params: Record<string, string>): string {
  const url = new URL(`${config.url}/rest/v1/${table}`);
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value);
  return url.toString();
}

async function expectOk(resp: APIResponse, context: string): Promise<void> {
  if (resp.ok()) return;
  const body = await resp.text().catch(() => '');
  throw new Error(`${context} failed: HTTP ${resp.status()} ${body.slice(0, 500)}`);
}

async function restSelect<T>(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  table: string,
  params: Record<string, string>,
): Promise<T[]> {
  const resp = await request.get(restUrl(config, table, params), {
    headers: supabaseAdminHeaders(config),
    timeout: API_REQUEST_TIMEOUT,
  });
  await expectOk(resp, `select ${table}`);
  return await resp.json() as T[];
}

async function restInsertOne<T>(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  table: string,
  data: Record<string, unknown>,
): Promise<T> {
  const resp = await request.post(restUrl(config, table, {}), {
    headers: supabaseAdminHeaders(config, { Prefer: 'return=representation' }),
    data,
    timeout: API_REQUEST_TIMEOUT,
  });
  await expectOk(resp, `insert ${table}`);
  const rows = await resp.json() as T[];
  expect(rows.length).toBe(1);
  return rows[0];
}

async function ensureLinkedEmployee(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  auth: AuthContext,
): Promise<EmployeeSetup> {
  const existing = await restSelect<EmployeeSetup>(request, config, 'employees', {
    select: 'id',
    tenant_id: `eq.${auth.tenantId}`,
    user_id: `eq.${auth.userId}`,
    deleted_at: 'is.null',
    limit: '1',
  });
  if (existing[0]?.id) return existing[0];

  const meta = loadLoginMeta();
  return await restInsertOne<EmployeeSetup>(request, config, 'employees', {
    tenant_id: auth.tenantId,
    user_id: auth.userId,
    first_name: 'Copilot',
    last_name: 'Verifier',
    email: meta?.email ?? `copilot-verifier-${auth.userId}@aethos-qa.dev`,
    title: 'Copilot Verification User',
    employment_type: 'full_time',
    default_bill_rate: '175.00',
    default_bill_rate_currency: 'USD',
    cost_rate: '85.00',
    available_hours_per_week: '40.00',
    status: 'active',
  });
}

async function findProjectByName(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  tenantId: string,
  name: string,
): Promise<ProjectSetup | null> {
  const rows = await restSelect<ProjectSetup>(request, config, 'projects', {
    select: 'id,name',
    tenant_id: `eq.${tenantId}`,
    name: `eq.${name}`,
    status: 'eq.active',
    deleted_at: 'is.null',
    limit: '1',
  });
  return rows[0] ?? null;
}

async function ensureFallbackProject(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  tenantId: string,
): Promise<ProjectSetup> {
  const existing = await findProjectByName(request, config, tenantId, FALLBACK_PROJECT_NAME);
  if (existing) return existing;

  const clientRows = await restSelect<{ id: string }>(request, config, 'clients', {
    select: 'id',
    tenant_id: `eq.${tenantId}`,
    name: 'eq.Copilot Verification Client [E2E]',
    kind: 'eq.customer',
    deleted_at: 'is.null',
    limit: '1',
  });
  const client = clientRows[0] ?? await restInsertOne<{ id: string }>(request, config, 'clients', {
    tenant_id: tenantId,
    name: 'Copilot Verification Client [E2E]',
    legal_name: 'Copilot Verification Client [E2E]',
    kind: 'customer',
    currency: 'USD',
  });

  const engagement = await restInsertOne<{ id: string }>(request, config, 'engagements', {
    tenant_id: tenantId,
    client_id: client.id,
    name: 'Copilot Verification Engagement [E2E]',
    billing_arrangement: 'time_and_materials',
    currency: 'USD',
    total_value: '10000.00',
    status: 'active',
    description: 'Created by live Copilot log-time verification.',
  });

  return await restInsertOne<ProjectSetup>(request, config, 'projects', {
    tenant_id: tenantId,
    engagement_id: engagement.id,
    name: FALLBACK_PROJECT_NAME,
    description: 'Created by live Copilot log-time verification.',
    status: 'active',
    currency: 'USD',
    budget: '10000.00',
    budget_hours: '80.00',
  });
}

async function ensureActiveProject(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  tenantId: string,
): Promise<ProjectSetup> {
  const demoProject = await findProjectByName(request, config, tenantId, DEMO_PROJECT_NAME);
  if (demoProject) return demoProject;

  const anyActive = await restSelect<ProjectSetup>(request, config, 'projects', {
    select: 'id,name',
    tenant_id: `eq.${tenantId}`,
    status: 'eq.active',
    deleted_at: 'is.null',
    limit: '1',
  });
  if (anyActive[0]) return anyActive[0];

  return await ensureFallbackProject(request, config, tenantId);
}

async function listOpenCopilotTasks(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  tenantId: string,
): Promise<HitlTaskRow[]> {
  return await restSelect<HitlTaskRow>(request, config, 'hitl_tasks', {
    select: 'id,title,payload,created_at',
    tenant_id: `eq.${tenantId}`,
    kind: 'eq.copilot_log_time_entry',
    status: 'eq.open',
    order: 'created_at.desc',
    limit: '25',
  });
}

function taskMatchesDescription(task: HitlTaskRow, description: string): boolean {
  const payload = task.payload ?? {};
  const toolInput = payload['tool_input'];
  return (
    typeof toolInput === 'object' &&
    toolInput !== null &&
    String((toolInput as Record<string, unknown>)['description'] ?? '') === description
  );
}

async function findTimeEntryByDescription(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  tenantId: string,
  description: string,
): Promise<TimeEntryRow | null> {
  const rows = await restSelect<TimeEntryRow>(request, config, 'time_entries', {
    select: 'id,tenant_id,project_id,employee_id,hours,date,description,billable,billing_status,status',
    tenant_id: `eq.${tenantId}`,
    description: `eq.${description}`,
    deleted_at: 'is.null',
    limit: '1',
  });
  return rows[0] ?? null;
}

async function ensureAppRoute(page: Page, route: string): Promise<void> {
  await page.goto(`${BASE}${route}`, { waitUntil: 'domcontentloaded' });
  const shellReady = await page
    .getByRole('navigation', { name: /main navigation/i })
    .isVisible({ timeout: 10_000 })
    .catch(() => false);
  if (shellReady) return;

  const meta = loadLoginMeta();
  if (!meta) throw new Error('No login metadata found for refreshed UI session');
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' });
  await page.locator('#email').fill(meta.email);
  await page.locator('#password').fill(meta.password);
  await page.getByRole('button', { name: /^sign in$/i }).click();
  await page.waitForURL(/\/app\//, { timeout: 60_000 });
  await page.goto(`${BASE}${route}`, { waitUntil: 'domcontentloaded' });
}

test.describe('Copilot log_time_entry live tool flow (#253)', () => {
  test.use({ storageState: STORAGE_PATH });

  test.beforeEach(() => {
    test.skip(!fs.existsSync(STORAGE_PATH), 'no signed-in O2C tenant session');
    test.skip(!supabaseAdminConfig(), 'Supabase admin config missing');
    test.skip(!envValue('OPENROUTER_API_KEY'), 'OPENROUTER_API_KEY missing');
  });

  test('logs billable time through Copilot, Inbox approval, and Time Entries UI', async ({ page, request }) => {
    test.setTimeout(300_000);
    const auth = getAuthFromStorage();
    const config = supabaseAdminConfig();
    test.skip(!auth || !config, 'auth or Supabase admin config missing');

    const employee = await ensureLinkedEmployee(request, config!, auth!);
    const project = await ensureActiveProject(request, config!, auth!.tenantId);
    const today = new Date().toISOString().slice(0, 10);
    const description = `Copilot live issue two five three ${randomUUID()}`;

    await expect
      .poll(async () => await findTimeEntryByDescription(request, config!, auth!.tenantId, description), {
        timeout: 5_000,
        message: 'description should be unique before the live run',
      })
      .toBeNull();

    await ensureAppRoute(page, '/app/copilot');
    await expect(page.getByRole('button', { name: /new chat/i })).toBeVisible({ timeout: 30_000 });
    await page.getByRole('button', { name: /new chat/i }).click();

    const prompt = [
      `Log exactly 4.5 billable hours on project "${project.name}" for ${today}.`,
      `Use this exact description: "${description}".`,
      'Use the log_time_entry tool and create the review task without asking a follow-up question.',
    ].join(' ');
    await page.getByLabel('Message input').fill(prompt);
    await page.getByRole('button', { name: /send message/i }).click();

    await expect(page.getByLabel('Tool completed: log_time_entry')).toBeVisible({ timeout: 150_000 });

    let resolvedTaskId = '';
    await expect
      .poll(async () => {
        const tasks = await listOpenCopilotTasks(request, config!, auth!.tenantId);
        resolvedTaskId = tasks.find(task => taskMatchesDescription(task, description))?.id ?? '';
        return resolvedTaskId;
      }, {
        timeout: 45_000,
        message: 'Copilot should create an open HITL task for the write',
      })
      .not.toBe('');

    await page.goto(`${BASE}/app/inbox`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: /^inbox$/i })).toBeVisible({ timeout: 30_000 });
    const taskCard = page.locator(`#task-${resolvedTaskId}`);
    await expect(taskCard).toBeVisible({ timeout: 30_000 });
    await taskCard.getByRole('button', { name: /approve/i }).click();
    await expect(taskCard).toBeHidden({ timeout: 30_000 });

    let materialised: TimeEntryRow | null = null;
    await expect
      .poll(async () => {
        materialised = await findTimeEntryByDescription(request, config!, auth!.tenantId, description);
        return materialised?.id ?? '';
      }, {
        timeout: 45_000,
        message: 'approved HITL task should materialise a real time entry',
      })
      .not.toBe('');

    expect(materialised).not.toBeNull();
    expect(materialised?.project_id).toBe(project.id);
    expect(materialised?.employee_id).toBe(employee.id);
    expect(String(materialised?.hours)).toMatch(/^4\.5(0)?$/);
    expect(materialised?.date).toBe(today);
    expect(materialised?.billable).toBe(true);
    expect(materialised?.billing_status).toBe('unbilled');

    await page.goto(`${BASE}/app/time`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: /^time entries$/i })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(description)).toBeVisible({ timeout: 30_000 });
  });
});
