/**
 * Live Copilot tool-use verification for #263.
 *
 * Browser flow:
 * Copilot chat -> draft_invoice tool -> HITL Inbox approval -> Invoices UI.
 */

import { test, expect, APIRequestContext, APIResponse, Page } from '@playwright/test';
import { Buffer } from 'node:buffer';
import { randomUUID } from 'node:crypto';
import * as fs from 'node:fs';
import * as path from 'node:path';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'http://localhost:4201';
const API = process.env.AETHOS_PS_API_URL ?? 'http://localhost:8011';
const STORAGE_PATH = path.join(__dirname, '.auth', 'o2c-tenant.json');
const META_PATH = path.join(__dirname, '.auth', 'o2c-tenant.meta.json');
const API_REQUEST_TIMEOUT = 90_000;

type AuthContext = { token: string; tenantId: string; userId: string };
type LoginCredentials = { email: string; password: string };
type SupabaseAdminConfig = { url: string; serviceRoleKey: string };
type ClientRow = { id: string; name: string };
type EngagementRow = { id: string; name: string };
type HitlTaskRow = { id: string; title: string; payload?: Record<string, unknown> };
type InvoiceRow = {
  id: string;
  invoice_number: string;
  status: string;
  total: string | number;
  currency: string;
  engagement_id: string;
  client_id: string;
};

function envValue(name: string): string {
  if (process.env[name]) return process.env[name]!;
  for (const file of [
    path.join(__dirname, '..', '..', '.env'),
    path.join(__dirname, '..', '..', 'backend', '.env'),
  ]) {
    if (!fs.existsSync(file)) continue;
    const line = fs
      .readFileSync(file, 'utf-8')
      .split(/\r?\n/)
      .find((row) => row.trim().startsWith(`${name}=`));
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
  } catch {
    /* no-op */
  }
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
          try {
            token = JSON.parse(ls.value)?.access_token ?? token;
          } catch {
            /* no-op */
          }
        }
        if (!token && ls.name === 'aethos_token') token = ls.value;
        if (ls.name === 'aethos_tenant_id') tenantId = ls.value;
      }
    }
    const userId = parseJwtSub(token);
    if (token && tenantId && userId) return { token, tenantId, userId };
  } catch {
    /* no-op */
  }
  return null;
}

function supabaseAdminConfig(): SupabaseAdminConfig | null {
  const url = envValue('SUPABASE_URL');
  const serviceRoleKey = envValue('SUPABASE_SERVICE_ROLE_KEY');
  if (!url || !serviceRoleKey) return null;
  return { url, serviceRoleKey };
}

function apiHeaders(auth: AuthContext): Record<string, string> {
  return {
    Authorization: `Bearer ${auth.token}`,
    'X-Tenant-ID': auth.tenantId,
    'Content-Type': 'application/json',
  };
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

async function createFixedFeeEngagement(
  request: APIRequestContext,
  auth: AuthContext,
): Promise<{ client: ClientRow; engagement: EngagementRow; total: string }> {
  const suffix = randomUUID().slice(0, 8);
  const total = '12345.67';
  const clientName = `Copilot Invoice Client ${suffix} [E2E]`;
  const engagementName = `Copilot Invoice Draft ${suffix} [E2E]`;

  const clientResp = await request.post(`${API}/api/v1/clients`, {
    headers: apiHeaders(auth),
    data: {
      name: clientName,
      legal_name: clientName,
      kind: 'customer',
      currency: 'USD',
    },
    timeout: API_REQUEST_TIMEOUT,
  });
  await expectOk(clientResp, 'create invoice client');
  const client = await clientResp.json() as ClientRow;

  const engagementResp = await request.post(`${API}/api/v1/engagements`, {
    headers: apiHeaders(auth),
    data: {
      client_id: client.id,
      name: engagementName,
      billing_arrangement: 'fixed_fee',
      currency: 'USD',
      total_value: total,
      billing_terms: { fixed_fee_amount: total },
    },
    timeout: API_REQUEST_TIMEOUT,
  });
  await expectOk(engagementResp, 'create fixed-fee engagement');
  const engagement = await engagementResp.json() as EngagementRow;

  return { client, engagement, total };
}

async function listOpenCopilotInvoiceTasks(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  tenantId: string,
): Promise<HitlTaskRow[]> {
  return await restSelect<HitlTaskRow>(request, config, 'hitl_tasks', {
    select: 'id,title,payload,created_at',
    tenant_id: `eq.${tenantId}`,
    kind: 'eq.copilot_draft_invoice',
    status: 'eq.open',
    order: 'created_at.desc',
    limit: '25',
  });
}

function taskMatchesEngagement(task: HitlTaskRow, engagementId: string): boolean {
  const payload = task.payload ?? {};
  const invoiceDraft = payload['invoice_draft'];
  return (
    typeof invoiceDraft === 'object' &&
    invoiceDraft !== null &&
    String((invoiceDraft as Record<string, unknown>)['engagement_id'] ?? '') === engagementId
  );
}

async function findInvoiceByEngagement(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  tenantId: string,
  engagementId: string,
): Promise<InvoiceRow | null> {
  const rows = await restSelect<InvoiceRow>(request, config, 'invoices', {
    select: 'id,invoice_number,status,total,currency,engagement_id,client_id',
    tenant_id: `eq.${tenantId}`,
    engagement_id: `eq.${engagementId}`,
    deleted_at: 'is.null',
    limit: '1',
  });
  return rows[0] ?? null;
}

test.describe('Copilot draft_invoice live tool flow (#263)', () => {
  test.use({ storageState: STORAGE_PATH });

  test.beforeEach(() => {
    test.skip(!fs.existsSync(STORAGE_PATH), 'no signed-in O2C tenant session');
    test.skip(!supabaseAdminConfig(), 'Supabase admin config missing');
    test.skip(!envValue('OPENROUTER_API_KEY'), 'OPENROUTER_API_KEY missing');
  });

  test('drafts a customer invoice through Copilot, Inbox approval, and Invoices UI', async ({ page, request }) => {
    test.setTimeout(300_000);
    const auth = getAuthFromStorage();
    const config = supabaseAdminConfig();
    test.skip(!auth || !config, 'auth or Supabase admin config missing');

    const seed = await createFixedFeeEngagement(request, auth!);

    await expect
      .poll(async () => await findInvoiceByEngagement(request, config!, auth!.tenantId, seed.engagement.id), {
        timeout: 5_000,
        message: 'engagement should not have an invoice before the live run',
      })
      .toBeNull();

    await ensureAppRoute(page, '/app/copilot');
    await expect(page.getByRole('button', { name: /new chat/i })).toBeVisible({ timeout: 30_000 });
    await page.getByRole('button', { name: /new chat/i }).click();

    const prompt = [
      `Draft a customer invoice for engagement "${seed.engagement.name}" for period ending 2026-06-30.`,
      'Use the draft_invoice tool.',
      'Create the Inbox review task without asking a follow-up question.',
      'Do not approve, send, or collect payment.',
    ].join(' ');
    await page.getByLabel('Message input').fill(prompt);
    await page.getByRole('button', { name: /send message/i }).click();

    let resolvedTaskId = '';
    await expect
      .poll(async () => {
        const tasks = await listOpenCopilotInvoiceTasks(request, config!, auth!.tenantId);
        resolvedTaskId = tasks.find((task) => taskMatchesEngagement(task, seed.engagement.id))?.id ?? '';
        return resolvedTaskId;
      }, {
        timeout: 150_000,
        message: 'Copilot should create an open HITL task for the invoice draft',
      })
      .not.toBe('');

    await page.goto(`${BASE}/app/inbox`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: /^inbox$/i })).toBeVisible({ timeout: 30_000 });
    const taskCard = page.locator(`#task-${resolvedTaskId}`);
    await expect(taskCard).toBeVisible({ timeout: 30_000 });
    await expect(taskCard).toContainText(seed.engagement.name, { timeout: 10_000 });
    await expect(taskCard).toContainText('total: 12345.67', { timeout: 10_000 });
    await expect(taskCard).toContainText('line count: 1', { timeout: 10_000 });
    await taskCard.getByRole('button', { name: /^approve/i }).click();
    await expect(taskCard).toBeHidden({ timeout: 30_000 });

    let invoice: InvoiceRow | null = null;
    await expect
      .poll(async () => {
        invoice = await findInvoiceByEngagement(request, config!, auth!.tenantId, seed.engagement.id);
        return invoice?.id ?? '';
      }, {
        timeout: 45_000,
        message: 'approved HITL task should materialise a draft invoice',
      })
      .not.toBe('');

    expect(invoice).not.toBeNull();
    expect(invoice?.status).toBe('draft');
    expect(invoice?.currency).toBe('USD');
    expect(String(invoice?.total)).toMatch(/^12345\.67$/);
    expect(invoice?.client_id).toBe(seed.client.id);

    await page.goto(`${BASE}/app/invoices`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: /^invoices$/i })).toBeVisible({ timeout: 30_000 });
    const invoiceRow = page.getByRole('row').filter({ hasText: invoice!.invoice_number });
    await expect(invoiceRow).toBeVisible({ timeout: 30_000 });
    await expect(invoiceRow).toContainText(seed.client.name);
    await expect(invoiceRow).toContainText('Draft');
  });
});
