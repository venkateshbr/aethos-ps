import { defineConfig, devices } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import * as fs from 'node:fs';
import * as path from 'node:path';

// Pre-seed the storage-state file BEFORE Playwright's config parses
// `use.storageState`. The `setup` project rewrites this file each run; this
// bootstrap step is purely to keep the loader from ENOENT-ing on a fresh
// checkout / cleaned worktree where e2e/.auth/storage-state.json does not
// yet exist. See e2e/global.setup.ts for the real session bootstrap.
// Apply local-dev defaults for env vars that specs read directly.
// CI overrides these via the shell environment; local runs just work without extra setup.
process.env.AETHOS_PS_WEB_URL ??= 'http://localhost:4201';
process.env.AETHOS_PS_API_URL ??= 'http://localhost:8011';
// Every Playwright runner owns only the tenants/auth files it creates. The ID
// is inherited by setup, workers, and global teardown, preventing a focused
// run from deleting another concurrent run's tenant.
process.env.AETHOS_E2E_RUN_ID ??= randomUUID();

const STORAGE_STATE = path.join(__dirname, 'e2e', '.auth', 'storage-state.json');
if (!fs.existsSync(STORAGE_STATE)) {
  fs.mkdirSync(path.dirname(STORAGE_STATE), { recursive: true });
  fs.writeFileSync(STORAGE_STATE, JSON.stringify({ cookies: [], origins: [] }));
}

/**
 * Playwright config for Aethos PS frontend e2e.
 *
 * Conventions from agent-harness/core/e2e-workflow-standard.md:
 *  - Single browser instance per run.
 *  - Storage state reused across tests within a run.
 *  - `--headed --slow-mo=300` locally; headless in CI.
 *  - Role-based locators; web-first assertions.
 */
export default defineConfig({
  testDir: './e2e',
  // The retained-production journey has its own no-teardown config and an
  // explicit mutation opt-in. Never let the ordinary suite discover it.
  testIgnore: /ishantech-production-ui\.spec\.ts/,
  globalTeardown: './e2e/global.teardown.ts',
  fullyParallel: false,             // single-session login; serial within project
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,                       // single browser for shared session pattern
  reporter: [
    ['list'],
    ['html', { open: 'never' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
  ],

  use: {
    baseURL: process.env.AETHOS_PS_WEB_URL ?? 'http://localhost:4201',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
    actionTimeout: 60_000,
    navigationTimeout: 60_000,
    headless: !!process.env.CI,
    launchOptions: {
      slowMo: process.env.CI ? 0 : 300,
    },
    storageState: 'e2e/.auth/storage-state.json',
  },

  projects: [
    {
      name: 'setup',
      testMatch: /global\.setup\.ts/,
    },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },
  ],

  outputDir: 'test-results/artifacts',
});
