import { expect, test, type Page } from '@playwright/test';

/**
 * The guide library moved from public `/guides` to `/app/guides` behind
 * authGuard + adminGuard, because it now publishes the Nous runtime and
 * learning-operations manual (secret rotation, open security gaps).
 *
 * These specs need no backend: guide HTML is a static asset and the guards
 * read the session from localStorage, so a seeded session exercises the real
 * routing, guard, rendering and export affordances.
 */

async function seedSession(page: Page, role: string): Promise<void> {
  await page.addInitScript(([r]) => {
    localStorage.setItem('aethos_token', 'e2e-fake-token');
    localStorage.setItem('aethos_tenant_id', '00000000-0000-0000-0000-000000000001');
    localStorage.setItem('aethos_role', r as string);
    localStorage.setItem('aethos_must_change_password', 'false');
  }, [role]);
}

test.describe('Guide library access control', () => {
  test('anonymous visitors cannot reach the library', async ({ page }) => {
    await page.goto('/app/guides');

    await expect(page).not.toHaveURL(/\/app\/guides/);
    await expect(page.getByRole('heading', { name: /learn aethos at your pace/i })).toBeHidden();
  });

  test('the old public /guides link redirects into the app', async ({ page }) => {
    await seedSession(page, 'owner');
    await page.goto('/guides');

    await expect(page).toHaveURL(/\/app\/guides$/);
    await expect(page.getByRole('heading', { name: /learn aethos at your pace/i })).toBeVisible();
  });

  test('a non-administrative role is redirected away', async ({ page }) => {
    await seedSession(page, 'member');
    await page.goto('/app/guides');

    await expect(page).toHaveURL(/\/app\/dashboard/);
    await expect(page.getByRole('heading', { name: /learn aethos at your pace/i })).toBeHidden();
  });
});

test.describe('Guide library for owners and admins', () => {
  test.beforeEach(async ({ page }) => {
    await seedSession(page, 'admin');
  });

  test('lists guides, filters them, and opens one', async ({ page }) => {
    await page.goto('/app/guides');

    await expect(page.getByRole('link', { name: /aethos ps platform user guide/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /nous on hermes/i })).toBeVisible();

    await page.getByRole('searchbox', { name: /search guides/i }).fill('prompt');
    await expect(page.getByRole('link', { name: /aethos nous prompt library/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /scenario-based demo guide v2/i })).toBeHidden();

    await page.getByRole('link', { name: /aethos nous prompt library/i }).click();
    await expect(page).toHaveURL(/\/app\/guides\/nous-prompt-library$/);
    await expect(page.getByRole('heading', { level: 1, name: /aethos nous prompt library/i })).toBeVisible();
    await expect(page.locator('article table').first()).toBeVisible();
  });

  test('renders the Hermes operations manual with its runtime sections', async ({ page }) => {
    await page.goto('/app/guides/nous-hermes-operations');

    await expect(
      page.getByRole('heading', { level: 1, name: /nous on hermes/i }),
    ).toBeVisible();
    await expect(page.getByRole('navigation', { name: /on this page/i })).toBeVisible();
    await expect(page.locator('article')).toContainText('self-learning loop');
  });

  test('offers a PDF export that opens the print pipeline', async ({ page }) => {
    await page.goto('/app/guides/platform-user-guide');

    // window.print() opens a native dialog Playwright cannot dismiss; assert the
    // control invokes it rather than letting the dialog block the run.
    await page.evaluate(() => {
      (window as unknown as { __printed: number }).__printed = 0;
      window.print = () => {
        (window as unknown as { __printed: number }).__printed += 1;
      };
    });

    const exportButton = page.getByRole('button', { name: /export this guide as a pdf/i });
    await expect(exportButton).toBeVisible();
    await exportButton.click();

    const printed = await page.evaluate(
      () => (window as unknown as { __printed: number }).__printed,
    );
    expect(printed).toBe(1);
  });

  test('keeps guide content usable on a narrow viewport', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/app/guides/platform-user-guide');

    await expect(page.getByRole('heading', { level: 1, name: /aethos ps platform user guide/i })).toBeVisible();

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(overflow).toBe(false);
  });
});
