import { defineConfig, devices } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

// Raw traces contain entered credentials and provider responses. Restrict all
// reporter/artifact files created by this dedicated process by default.
process.umask(0o077);

const PRODUCTION_ORIGIN = 'https://aethos.ishirock.tech';
const MUTATION_CONSENT = 'I_UNDERSTAND_THIS_MUTATES_PRODUCTION';
const CONFIG_MARKER = 'ishantech-retained-v1';

function requireExact(name: string, actual: string | undefined, expected: string): void {
  if (actual !== expected) {
    throw new Error(`${name} must equal ${JSON.stringify(expected)} for the retained production run.`);
  }
}

requireExact('AETHOS_RUN_ISHANTECH_PRODUCTION_UI', process.env.AETHOS_RUN_ISHANTECH_PRODUCTION_UI, MUTATION_CONSENT);
requireExact(
  'AETHOS_PS_WEB_URL',
  (process.env.AETHOS_PS_WEB_URL ?? '').replace(/\/$/, ''),
  PRODUCTION_ORIGIN,
);

const expectedSha = process.env.AETHOS_EXPECTED_DEPLOY_SHA ?? '';
if (!/^[0-9a-f]{40}$/.test(expectedSha)) {
  throw new Error('AETHOS_EXPECTED_DEPLOY_SHA must be the exact 40-character lowercase Git SHA deployed to production.');
}

const runId = process.env.AETHOS_ISHANTECH_RUN_ID ?? '';
if (!/^ISH-E2E-[0-9]{8}$/.test(runId)) {
  throw new Error('AETHOS_ISHANTECH_RUN_ID must match ISH-E2E-YYYYMMDD.');
}

const credentialPath = path.resolve(__dirname, '..', 'ishantech_e2e_credentials.json');
if (!fs.existsSync(credentialPath)) {
  throw new Error(`Missing ignored credential manifest: ${credentialPath}`);
}
if ((fs.statSync(credentialPath).mode & 0o077) !== 0) {
  throw new Error('ishantech_e2e_credentials.json must be owner-readable only (mode 0600).');
}

const credentialManifest = JSON.parse(fs.readFileSync(credentialPath, 'utf8')) as {
  run_id?: unknown;
  production_url?: unknown;
  company?: unknown;
  retained?: unknown;
  accounts?: unknown[];
};
requireExact('credential manifest run_id', String(credentialManifest.run_id ?? ''), runId);
requireExact(
  'credential manifest production_url',
  String(credentialManifest.production_url ?? '').replace(/\/$/, ''),
  PRODUCTION_ORIGIN,
);
requireExact('credential manifest company', String(credentialManifest.company ?? ''), 'Ishantech Advisory Pte. Ltd.');
if (credentialManifest.retained !== true || credentialManifest.accounts?.length !== 22) {
  throw new Error('Credential manifest must retain the tenant and contain exactly 22 accounts.');
}

process.env.AETHOS_PRODUCTION_UI_CONFIG = CONFIG_MARKER;

const evidenceRoot = path.resolve(__dirname, '..', 'ishantech_e2e_private_evidence', runId);
fs.mkdirSync(evidenceRoot, { recursive: true, mode: 0o700 });
fs.chmodSync(evidenceRoot, 0o700);

export default defineConfig({
  testDir: './e2e',
  testMatch: /ishantech-production-ui\.spec\.ts/,
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  timeout: 4 * 60 * 60 * 1000,
  expect: { timeout: 30_000 },
  reporter: [
    ['list'],
    ['html', { outputFolder: path.join(evidenceRoot, 'html-report'), open: 'never' }],
    ['json', { outputFile: path.join(evidenceRoot, 'playwright-results.json') }],
    ['junit', { outputFile: path.join(evidenceRoot, 'junit.xml') }],
  ],
  use: {
    ...devices['Desktop Chrome'],
    baseURL: PRODUCTION_ORIGIN,
    storageState: { cookies: [], origins: [] },
    headless: false,
    actionTimeout: 60_000,
    navigationTimeout: 60_000,
    screenshot: 'on',
    trace: 'on',
    video: {
      mode: 'on',
      size: { width: 1440, height: 900 },
    },
    viewport: { width: 1440, height: 900 },
    launchOptions: { slowMo: 150 },
  },
  projects: [{ name: 'chromium' }],
  outputDir: path.join(evidenceRoot, 'playwright-artifacts'),
  preserveOutput: 'always',
});
