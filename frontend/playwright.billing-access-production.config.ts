import { defineConfig, devices } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

process.umask(0o077);

const origin = 'https://aethos.ishirock.tech';
if (process.env.AETHOS_RUN_BILLING_ACCESS_PRODUCTION !== 'I_UNDERSTAND_THIS_TARGETS_PRODUCTION') {
  throw new Error('Explicit production billing-access consent is required.');
}
if ((process.env.AETHOS_PS_WEB_URL ?? '').replace(/\/$/, '') !== origin) {
  throw new Error(`AETHOS_PS_WEB_URL must equal ${origin}.`);
}
if (!/^[0-9a-f]{40}$/.test(process.env.AETHOS_EXPECTED_DEPLOY_SHA ?? '')) {
  throw new Error('AETHOS_EXPECTED_DEPLOY_SHA must be an exact Git SHA.');
}
if (!['trial_expired', 'override_active'].includes(process.env.AETHOS_EXPECTED_BILLING_STATUS ?? '')) {
  throw new Error('AETHOS_EXPECTED_BILLING_STATUS must be trial_expired or override_active.');
}

const credentialPath = path.resolve(__dirname, '..', 'sterlingbridge_e2e_credentials.json');
if (!fs.existsSync(credentialPath) || (fs.statSync(credentialPath).mode & 0o077) !== 0) {
  throw new Error('The ignored Sterling credential manifest must exist with mode 0600.');
}

const evidenceRoot = path.resolve(__dirname, '..', 'billing_access_e2e_private_evidence');
fs.mkdirSync(evidenceRoot, { recursive: true, mode: 0o700 });

export default defineConfig({
  testDir: './e2e',
  testMatch: /expired-trial-access-production\.spec\.ts/,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { outputFolder: path.join(evidenceRoot, 'html'), open: 'never' }]],
  use: {
    ...devices['Desktop Chrome'],
    baseURL: origin,
    storageState: { cookies: [], origins: [] },
    headless: true,
    screenshot: 'on',
    trace: 'on',
  },
  outputDir: path.join(evidenceRoot, 'artifacts'),
});
