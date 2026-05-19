import { defineConfig, devices } from '@playwright/test';

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
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
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
