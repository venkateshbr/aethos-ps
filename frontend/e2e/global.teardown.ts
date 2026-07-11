/**
 * Remove run-scoped tenants created by the default real-stack Playwright suite.
 *
 * Product data may prevent a safe hard delete, so teardown deletes the test
 * Stripe customer and auth identities, clears memberships, and marks the
 * guarded tenant deleted. It never matches retained demo or Ishantech tenants.
 */

import { createClient } from '@supabase/supabase-js';
import * as fs from 'node:fs';
import * as path from 'node:path';
import WebSocket from 'ws';

const AUTH_DIR = path.join(__dirname, '.auth');
const REPO_ROOT = path.resolve(__dirname, '../..');
const RUN_LOCK_PATH = path.join(AUTH_DIR, 'playwright-run.lock');
const TIMESHEET_SEED_PATH = path.join(AUTH_DIR, 'timesheet-e2e-seed.json');
const TIMESHEET_STATE_PATHS = [
  path.join(AUTH_DIR, 'ts-owner.json'),
  path.join(AUTH_DIR, 'ts-bob.json'),
  path.join(AUTH_DIR, 'ts-carol.json'),
];

type RunMetadata = {
  tenantId?: string | null;
  playwrightRunId?: string | null;
};

type CleanupTarget = {
  metaPath: string;
  storagePath: string;
  allowedNamePrefixes: string[];
};

const TARGETS: CleanupTarget[] = [
  {
    metaPath: path.join(AUTH_DIR, 'o2c-tenant.meta.json'),
    storagePath: path.join(AUTH_DIR, 'o2c-tenant.json'),
    allowedNamePrefixes: ['Aksha O2C '],
  },
  {
    metaPath: path.join(AUTH_DIR, 'isolation-tenant-b.meta.json'),
    storagePath: path.join(AUTH_DIR, 'isolation-tenant-b.json'),
    allowedNamePrefixes: ['Aksha B '],
  },
];

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

async function deleteStripeTestCustomer(customerId: string): Promise<void> {
  const secretKey = envValue('STRIPE_SECRET_KEY');
  if (!secretKey.startsWith('sk_test_')) {
    throw new Error('Refusing Playwright cleanup without a Stripe test-mode secret key.');
  }
  if (!customerId.startsWith('cus_')) {
    throw new Error('Refusing Playwright cleanup for an unexpected Stripe customer identifier.');
  }
  const response = await fetch(
    `https://api.stripe.com/v1/customers/${encodeURIComponent(customerId)}`,
    {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${secretKey}` },
    },
  );
  if (response.ok) return;
  const body = await response.json().catch(() => ({})) as {
    error?: { code?: string };
  };
  if (response.status === 404 && body.error?.code === 'resource_missing') return;
  throw new Error(`Stripe test-customer cleanup failed with status ${response.status}.`);
}

async function cleanupTarget(target: CleanupTarget): Promise<boolean> {
  if (!fs.existsSync(target.metaPath)) return false;

  const metadata = JSON.parse(fs.readFileSync(target.metaPath, 'utf-8')) as RunMetadata;
  const runId = process.env.AETHOS_E2E_RUN_ID;
  if (!runId || metadata.playwrightRunId !== runId) return false;
  const tenantId = String(metadata.tenantId || '');
  if (!tenantId) throw new Error(`Missing tenantId in ${path.basename(target.metaPath)}.`);

  const supabaseUrl = envValue('SUPABASE_URL');
  const serviceRoleKey = envValue('SUPABASE_SERVICE_ROLE_KEY');
  if (!supabaseUrl || !serviceRoleKey) {
    throw new Error('Supabase cleanup credentials are unavailable.');
  }
  const db = createClient(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false, autoRefreshToken: false },
    realtime: { transport: WebSocket },
  });
  const { data: tenants, error: tenantError } = await db
    .from('tenants')
    .select('id,name,status,stripe_customer_id')
    .eq('id', tenantId)
    .limit(1);
  if (tenantError) throw tenantError;
  const tenant = tenants?.[0];
  if (!tenant) {
    fs.rmSync(target.metaPath, { force: true });
    fs.rmSync(target.storagePath, { force: true });
    return true;
  }
  if (!target.allowedNamePrefixes.some((prefix) => String(tenant.name || '').startsWith(prefix))) {
    throw new Error('Refusing Playwright cleanup because the tenant name guard did not match.');
  }

  const { data: memberships, error: membershipReadError } = await db
    .from('tenant_users')
    .select('user_id')
    .eq('tenant_id', tenantId);
  if (membershipReadError) throw membershipReadError;

  const customerId = String(tenant.stripe_customer_id || '');
  if (customerId) await deleteStripeTestCustomer(customerId);

  // Employee invites link operational employee records to both the auth user
  // and tenant membership. Detach those nullable references before deleting
  // the run-scoped identities, otherwise the foreign keys make teardown fail.
  const { error: employeeDetachError } = await db
    .from('employees')
    .update({ user_id: null, tenant_user_id: null })
    .eq('tenant_id', tenantId);
  if (employeeDetachError) throw employeeDetachError;

  for (const membership of memberships || []) {
    const userId = String(membership.user_id || '');
    if (!userId) continue;
    fs.rmSync(path.join(AUTH_DIR, `o2c-viewer-${userId}.json`), { force: true });
    const { error } = await db.auth.admin.deleteUser(userId);
    if (error && !/not found/i.test(error.message)) throw error;
  }

  const { error: membershipDeleteError } = await db
    .from('tenant_users')
    .delete()
    .eq('tenant_id', tenantId);
  if (membershipDeleteError) throw membershipDeleteError;

  const { error: tenantUpdateError } = await db
    .from('tenants')
    .update({ status: 'deleted', stripe_subscription_status: 'canceled' })
    .eq('id', tenantId);
  if (tenantUpdateError) throw tenantUpdateError;

  const { count: membershipCount, error: verifyMembershipError } = await db
    .from('tenant_users')
    .select('id', { count: 'exact', head: true })
    .eq('tenant_id', tenantId);
  if (verifyMembershipError) throw verifyMembershipError;
  const { data: verifiedTenant, error: verifyTenantError } = await db
    .from('tenants')
    .select('status')
    .eq('id', tenantId)
    .limit(1);
  if (verifyTenantError) throw verifyTenantError;
  if ((membershipCount || 0) !== 0 || verifiedTenant?.[0]?.status !== 'deleted') {
    throw new Error('Playwright tenant cleanup verification failed.');
  }

  fs.rmSync(target.metaPath, { force: true });
  fs.rmSync(target.storagePath, { force: true });
  return true;
}

function cleanupTimesheetArtifactsForRun(): void {
  if (!fs.existsSync(TIMESHEET_SEED_PATH)) return;
  const metadata = JSON.parse(fs.readFileSync(TIMESHEET_SEED_PATH, 'utf-8')) as {
    playwright_run_id?: string | null;
  };
  const runId = process.env.AETHOS_E2E_RUN_ID;
  if (!runId || metadata.playwright_run_id !== runId) return;
  fs.rmSync(TIMESHEET_SEED_PATH, { force: true });
  for (const statePath of TIMESHEET_STATE_PATHS) fs.rmSync(statePath, { force: true });
}

export default async function globalTeardown(): Promise<void> {
  let cleaned = 0;
  try {
    for (const target of TARGETS) {
      if (await cleanupTarget(target)) {
        cleaned += 1;
        if (target.metaPath.endsWith('o2c-tenant.meta.json')) {
          cleanupTimesheetArtifactsForRun();
        }
      }
    }
  } finally {
    const runId = process.env.AETHOS_E2E_RUN_ID;
    if (runId && fs.existsSync(RUN_LOCK_PATH)) {
      const owner = fs.readFileSync(RUN_LOCK_PATH, 'utf-8').trim();
      if (owner === runId) fs.rmSync(RUN_LOCK_PATH, { force: true });
    }
  }
  console.log(`Playwright teardown cleaned ${cleaned} run-scoped tenant(s).`);
}
